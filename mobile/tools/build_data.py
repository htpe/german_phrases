"""Export the phrase CSVs to mobile/phrases.json for the phone app.

Run after changing data/phrases_*.csv:  python mobile/tools/build_data.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from phrase_loader import load_all  # noqa: E402

OUT = ROOT / "mobile" / "phrases.json"


def main() -> None:
    # Compact rows: [id, level, topic, german, english, chinese, [[de, en], ...]]
    rows = [[p.id, p.level, p.topic, p.german, p.english, p.chinese, [list(e) for e in p.examples]]
            for p in load_all()]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(rows)} phrases to {OUT}")


if __name__ == "__main__":
    main()
