"""Import phrases from a file into a named collection (data/phrases_<name>.csv).

A converter reads one file format into rows in the app's format. To support a new format,
write one function and register it:

    @converter("Anki export (.txt)", (".txt",))
    def anki_txt(path: Path) -> list[dict]:
        ...  # return [{"german": ..., "english": ..., "topic": ..., "chinese": ..., "examples": ...}]

Only "german" and "english" are required; "examples" uses the app format
"Satz. (Sentence.) | Satz 2. (Sentence 2.)". Registered converters appear in the import dialog.
"""
import csv
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from phrase_loader import DATA_DIR, LEVELS, collections

COLUMNS = ("id", "level", "topic", "german", "english", "chinese", "examples")
REQUIRED = ("german", "english")
_NAME_RE = re.compile(r"^[\w-]{1,20}$")


@dataclass(frozen=True)
class Converter:
    name: str                   # shown in the import dialog
    extensions: tuple[str, ...]  # for the file chooser, e.g. (".csv",)
    read: Callable[[Path], list[dict]]


CONVERTERS: dict[str, Converter] = {}


def converter(name: str, extensions: tuple[str, ...]):
    """Register a function that reads a file into rows (dicts) in the app's format."""
    def register(read: Callable[[Path], list[dict]]):
        CONVERTERS[name] = Converter(name, extensions, read)
        return read
    return register


@converter("App CSV (.csv)", (".csv",))
def app_csv(path: Path) -> list[dict]:
    """The format of data/phrases_B1.csv; comma, semicolon or tab separated. id/level are ignored."""
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        text = f.read()
    try:
        dialect = csv.Sniffer().sniff(text.split("\n", 1)[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    columns = {(c or "").strip().lower() for c in reader.fieldnames or []}
    missing = [c for c in REQUIRED if c not in columns]
    if missing:
        raise ValueError(f"The file has no column {', '.join(missing)}. "
                         f"Expected columns: {', '.join(COLUMNS[2:])} (german and english required).")
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]


def valid_name(name: str) -> str | None:
    """None if `name` can be used for a collection, else the reason why not."""
    if not _NAME_RE.match(name):
        return "Use 1-20 letters, digits, - or _ (no spaces)."
    if name.upper() in (*LEVELS, "ALL"):
        return f"{name} is a built-in level; choose another name."
    return None


def custom_collections(data_dir: Path = DATA_DIR) -> list[str]:
    return [name for name in collections(data_dir) if name not in LEVELS]


@dataclass
class ImportResult:
    added: int = 0
    duplicates: int = 0
    invalid: list[int] = field(default_factory=list)  # row numbers (1 = first data row)


def _read_collection(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def import_phrases(source: Path, name: str, converter_name: str = "App CSV (.csv)",
                   data_dir: Path = DATA_DIR) -> ImportResult:
    """Add the phrases of `source` to collection `name`, creating it if needed."""
    problem = valid_name(name)
    if problem:
        raise ValueError(problem)
    rows = CONVERTERS[converter_name].read(Path(source))
    target = data_dir / f"phrases_{name}.csv"
    existing = _read_collection(target)
    prefix = name.upper()
    numbers = [int(r["id"].rsplit("-", 1)[1]) for r in existing
               if r.get("id", "").rsplit("-", 1)[-1].isdigit()]
    next_number = max(numbers, default=0) + 1
    seen = {r["german"].strip().casefold() for r in existing}
    result = ImportResult()
    new_rows = []
    for number, row in enumerate(rows, 1):
        german, english = row.get("german", "").strip(), row.get("english", "").strip()
        if not german or not english:
            result.invalid.append(number)
            continue
        if german.casefold() in seen:
            result.duplicates += 1
            continue
        seen.add(german.casefold())
        new_rows.append({
            "id": f"{prefix}-{next_number:04d}", "level": name,
            "topic": row.get("topic", "").strip() or name, "german": german, "english": english,
            "chinese": row.get("chinese", "").strip(), "examples": row.get("examples", "").strip(),
        })
        next_number += 1
    result.added = len(new_rows)
    if new_rows:
        _write(target, [{c: r.get(c, "") for c in COLUMNS} for r in existing] + new_rows)
    return result


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file first so a crash never leaves a half-written file.
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)
