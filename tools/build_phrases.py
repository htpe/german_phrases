"""Merge, validate and deduplicate raw phrase chunks into the final level CSVs.

Reads data/chunks/{LEVEL}_*.csv (6 columns, no header):
    level, topic, german, english, chinese, examples
Writes data/phrases_{LEVEL}.csv with an id column and a header row.

IDs are stable: phrases already in the output file keep their ID (progress is keyed by ID),
new phrases are appended with the next numbers until the level reaches its target.

With --kind words, reads data/word_chunks/{LEVEL}_*.csv (same 6 columns) and writes the
collections data/phrases_Wort-{LEVEL}.csv (level "Wort-B1", IDs "WORT-B1-0001").

Usage: python tools/build_phrases.py [--kind phrases|words] [--target 1000] [--targets B2=1500,C1=1500]
"""
import argparse
import csv
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHUNK_DIR = ROOT / "data" / "chunks"
WORD_CHUNK_DIR = ROOT / "data" / "word_chunks"
OUT_DIR = ROOT / "data"
LEVELS = ["B1", "B2", "C1"]
HEADER = ["id", "level", "topic", "german", "english", "chinese", "examples"]

EXAMPLE_SEP = " | "
EXAMPLE_RE = re.compile(r"^(.*\S)\s+\(([^()]+)\)$")
CJK_RE = re.compile(r"[一-鿿]")


def normalize(german: str) -> str:
    """Key used for duplicate detection."""
    text = german.lower().replace("ß", "ss")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def validate(row: list[str], level: str) -> str | None:
    """Return a rejection reason, or None if the row is valid."""
    if len(row) != 6:
        return f"expected 6 fields, got {len(row)}"
    if any(not field.strip() for field in row):
        return "empty field"
    if row[0].strip() != level:
        return f"level mismatch: {row[0]!r}"
    if not CJK_RE.search(row[4]):
        return "chinese field has no CJK characters"
    examples = row[5].split(EXAMPLE_SEP)
    if len(examples) != 3:
        return f"expected 3 examples, got {len(examples)}"
    for ex in examples:
        if not EXAMPLE_RE.match(ex.strip()):
            return f"example not in 'German (English)' form: {ex[:60]!r}"
    return None


def read_level(level: str, rejects: Counter, chunk_dir: Path = CHUNK_DIR) -> list[list[str]]:
    rows = []
    for path in sorted(chunk_dir.glob(f"{level}_*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as f:
            for lineno, row in enumerate(csv.reader(f), 1):
                if not row or row == ["level", "topic", "german", "english", "chinese", "examples"]:
                    continue
                row = [field.strip() for field in row]
                reason = validate(row, level)
                if reason:
                    rejects[f"{path.name}:{lineno}: {reason}"] += 1
                    continue
                row[5] = EXAMPLE_SEP.join(ex.strip() for ex in row[5].split(EXAMPLE_SEP))
                rows.append(row)
    return rows


def balanced_trim(rows: list[list[str]], target: int) -> list[list[str]]:
    """Pick up to `target` rows round-robin across topics, preserving topic order."""
    by_topic: OrderedDict[str, list[list[str]]] = OrderedDict()
    for row in rows:
        by_topic.setdefault(row[1], []).append(row)
    if len(rows) <= target:
        return rows
    quota = {topic: 0 for topic in by_topic}
    picked = 0
    while picked < target:
        for topic, items in by_topic.items():
            if picked < target and quota[topic] < len(items):
                quota[topic] += 1
                picked += 1
    return [row for topic, items in by_topic.items() for row in items[: quota[topic]]]


def read_existing(path: Path) -> list[list[str]]:
    """Rows [id, level, topic, german, english, chinese, examples] of a previous build."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.reader(f) if row and row != HEADER]


def parse_targets(text: str, default: int) -> dict[str, int]:
    targets = dict.fromkeys(LEVELS, default)
    for item in filter(None, text.split(",")):
        level, _, number = item.partition("=")
        if level.strip().upper() not in LEVELS or not number.strip().isdigit():
            raise SystemExit(f"bad --targets entry {item!r}, expected e.g. B2=1500")
        targets[level.strip().upper()] = int(number)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("phrases", "words"), default="phrases")
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--targets", default="", help="per-level targets, e.g. B2=1500,C1=1500")
    args = parser.parse_args()
    targets = parse_targets(args.targets, args.target)
    words = args.kind == "words"
    chunk_dir = WORD_CHUNK_DIR if words else CHUNK_DIR

    seen: set[str] = set()  # across levels; lower level keeps the phrase
    ok = True
    for level in LEVELS:
        name = f"Wort-{level}" if words else level
        prefix = name.upper()
        target = targets[level]
        rejects: Counter = Counter()
        rows = read_level(level, rejects, chunk_dir)
        unique, dupes = [], 0
        for row in rows:
            key = normalize(row[2])
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            unique.append(row)

        # Keep every row of the previous build with its ID (updated from the chunks if present),
        # then fill up to the target with new rows.
        out_path = OUT_DIR / f"phrases_{name}.csv"
        by_key = {normalize(row[2]): row for row in unique}
        final, kept_keys = [], set()
        for old in read_existing(out_path):
            key = normalize(old[3])
            kept_keys.add(key)
            seen.add(key)
            final.append([old[0], *by_key.get(key, old[1:])])
        numbers = [int(row[0].rsplit("-", 1)[1]) for row in final]
        next_number = max(numbers, default=0) + 1
        fresh = [row for row in unique if normalize(row[2]) not in kept_keys]
        added = balanced_trim(fresh, max(target - len(final), 0)) if len(final) < target else []
        for i, row in enumerate(added, next_number):
            final.append([f"{prefix}-{i:04d}", *row])
        for row in final:
            row[1] = name

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(HEADER)
            writer.writerows(final)

        topics = Counter(row[2] for row in final)
        print(f"{name}: {len(rows)} valid, {dupes} duplicates, {sum(rejects.values())} rejected "
              f"-> {len(final)} written to {out_path.name} ({len(added)} new)")
        for topic, n in topics.items():
            print(f"    {n:4d}  {topic}")
        for reason in rejects:
            print(f"    REJECT {reason}")
        if len(final) < target:
            ok = False
            print(f"    SHORTFALL: {target - len(final)} entries missing")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
