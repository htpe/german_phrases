import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from progress import Progress


def card(last_review, reps):
    return {"reps": reps, "interval": 1, "ease": 2.5, "lapses": 0, "due": last_review,
            "last_review": last_review}


class MergeTest(unittest.TestCase):
    """The same case as the merge test in mobile/tests/parity.test.js."""

    def load(self, name, data):
        path = Path(self.tmp.name) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return Progress(path)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_merge_keeps_newer_reviews(self):
        shared = ["2026-10-01", "A", 3, 5, 1]
        here = self.load("here.json", {
            "settings": {"level": "B2"}, "daily": {"date": "2026-10-03", "new": 1, "reviews": 0},
            "starred": ["A"],
            "log": [shared, ["2026-10-03", "B", 3, 4, 1], ["2026-10-03", "C", 3, 2.0, 0]],
            "cards": {"A": card("2026-10-01", 1), "B": card("2026-10-03", 1),
                      "C": card("2026-10-03", 2)},
        })
        there = self.load("there.json", {
            "settings": {"level": "C1"}, "daily": {"date": "2026-10-03", "new": 0, "reviews": 2},
            "starred": ["D"],
            "log": [shared, ["2026-10-02", "A", 4, 3, 0], ["2026-10-03", "C", 3, 2, 0],
                    ["2026-10-03", "C", 4, 1, 0]],
            "cards": {"A": card("2026-10-02", 2), "B": card("2026-10-02", 5),
                      "C": card("2026-10-03", 3), "D": card("2026-10-01", 1)},
        })
        here.merge(there)
        self.assertEqual({pid: c.reps for pid, c in here.cards.items()},
                         {"A": 2, "B": 1, "C": 3, "D": 1})
        self.assertEqual(here.log, [shared, ["2026-10-02", "A", 4, 3, 0], ["2026-10-03", "B", 3, 4, 1],
                                    ["2026-10-03", "C", 3, 2.0, 0], ["2026-10-03", "C", 4, 1, 0]])
        self.assertEqual(here.starred, {"A", "D"})
        self.assertEqual(here.settings["level"], "B2")
        self.assertEqual(here.daily, {"date": "2026-10-03", "new": 1, "reviews": 2})

    def test_merging_a_copy_changes_nothing(self):
        data = {"daily": {"date": "2026-10-03", "new": 1, "reviews": 1},
                "log": [["2026-10-03", "A", 3, 60, 1], ["2026-10-03", "A", 3, 60, 0]],
                "cards": {"A": card("2026-10-03", 1)}}
        here, there = self.load("here.json", data), self.load("there.json", data)
        here.merge(there)
        self.assertEqual(here.log, data["log"])
        self.assertEqual(here.daily, data["daily"])


if __name__ == "__main__":
    unittest.main()
