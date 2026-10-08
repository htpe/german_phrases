"""Merge, validate and deduplicate raw phrase chunks into the final level CSVs.

Reads data/chunks/{LEVEL}_*.csv (6 columns, no header):
    level, topic, german, english, chinese, examples
Writes data/phrases_{LEVEL}.csv with an id column and a header row.

Usage: python tools/build_phrases.py [--target 1000]
"""
import argparse
import csv
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHUNK_DIR = ROOT / "data" / "chunks"
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


def read_level(level: str, rejects: Counter) -> list[list[str]]:
    rows = []
    for path in sorted(CHUNK_DIR.glob(f"{level}_*.csv")):
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=1000)
    args = parser.parse_args()

    seen: set[str] = set()  # across levels; lower level keeps the phrase
    ok = True
    for level in LEVELS:
        rejects: Counter = Counter()
        rows = read_level(level, rejects)
        unique, dupes = [], 0
        for row in rows:
            key = normalize(row[2])
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            unique.append(row)

        final = balanced_trim(unique, args.target)
        out_path = OUT_DIR / f"phrases_{level}.csv"
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(HEADER)
            for i, row in enumerate(final, 1):
                writer.writerow([f"{level}-{i:04d}", *row])

        topics = Counter(row[1] for row in final)
        print(f"{level}: {len(rows)} valid, {dupes} duplicates, "
              f"{sum(rejects.values())} rejected -> {len(final)} written to {out_path.name}")
        for topic, n in topics.items():
            print(f"    {n:4d}  {topic}")
        for reason in rejects:
            print(f"    REJECT {reason}")
        if len(final) < args.target:
            ok = False
            print(f"    SHORTFALL: {args.target - len(final)} phrases missing")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
