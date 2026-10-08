"""Load the phrase CSVs (built-in B1/B2/C1 plus imported collections) into Phrase objects."""
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
LEVELS = ("B1", "B2", "C1")  # built-in levels, rebuilt from data/chunks
_EXAMPLE_RE = re.compile(r"^(.*\S)\s+\(([^()]+)\)$")


@dataclass
class Phrase:
    id: str
    level: str
    topic: str
    german: str
    english: str
    chinese: str
    examples: list[tuple[str, str]] = field(default_factory=list)  # (german, english)


def parse_examples(raw: str) -> list[tuple[str, str]]:
    examples = []
    for part in raw.split("|"):
        part = part.strip()
        if not part:  # imported phrases may have no examples
            continue
        m = _EXAMPLE_RE.match(part)
        examples.append((m.group(1), m.group(2)) if m else (part, ""))
    return examples


def collections(data_dir: Path = DATA_DIR) -> list[str]:
    """Built-in levels first, then imported collections (data/phrases_<name>.csv), sorted."""
    found = sorted(path.stem.removeprefix("phrases_") for path in data_dir.glob("phrases_*.csv"))
    return [*LEVELS, *(name for name in found if name not in LEVELS)]


def load_phrases(level: str, data_dir: Path = DATA_DIR) -> list[Phrase]:
    if level.upper() in LEVELS:
        level = level.upper()
    elif level not in collections(data_dir):
        raise ValueError(f"unknown level {level!r}, expected one of {collections(data_dir)}")
    with (data_dir / f"phrases_{level}.csv").open(encoding="utf-8-sig", newline="") as f:
        return [
            Phrase(
                id=row["id"],
                level=row["level"],
                topic=row["topic"],
                german=row["german"],
                english=row["english"],
                chinese=row["chinese"],
                examples=parse_examples(row["examples"]),
            )
            for row in csv.DictReader(f)
        ]


def load_all(data_dir: Path = DATA_DIR) -> list[Phrase]:
    return [p for level in collections(data_dir) for p in load_phrases(level, data_dir)]


if __name__ == "__main__":
    for level in collections():
        phrases = load_phrases(level)
        print(f"{level}: {len(phrases)} phrases")
        if phrases:
            p = phrases[0]
            print(f"  {p.id} {p.german} = {p.english} / {p.chinese}")
            for de, en in p.examples:
                print(f"    - {de}  ->  {en}")
