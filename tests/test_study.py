import sys
import tempfile
import unittest
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phrase_loader import Phrase, load_all
from progress import Progress
from srs import AGAIN, GOOD
from study import AGAIN_GAP, StudySession, statistics

TODAY = date(2026, 1, 1)


def make_phrases(n: int) -> list[Phrase]:
    return [Phrase(f"B1-{i:04d}", "B1", "Topic", f"de {i}", f"en {i}", f"中 {i}",
                   [("Satz.", "Sentence.")] * 3) for i in range(1, n + 1)]


class StudySessionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "progress.json"
        self.progress = Progress(self.path)
        self.progress.settings["new_per_day"] = 5
        self.phrases = make_phrases(30)

    def tearDown(self):
        self.tmp.cleanup()

    def session(self, today=TODAY):
        return StudySession(self.phrases, self.progress, today)

    def test_new_limit(self):
        s = self.session()
        self.assertEqual(len(s.queue), 5)
        self.assertEqual(s.remaining(), {"new": 5, "review": 0})

    def test_new_limit_counts_cards_already_learned_today(self):
        s = self.session()
        s.rate(GOOD)
        s.rate(GOOD)
        self.assertEqual(len(self.session().queue), 3)

    def test_again_requeues_card(self):
        s = self.session()
        first = s.current
        s.rate(AGAIN)
        self.assertEqual(s.queue.index(first), AGAIN_GAP)
        self.assertEqual(len(s.queue), 5)

    def test_due_reviews_come_first_next_day(self):
        s = self.session()
        learned = s.current
        s.rate(GOOD)  # interval 1 day
        tomorrow = self.session(TODAY + timedelta(days=1))
        self.assertEqual(tomorrow.current, learned)
        self.assertEqual(tomorrow.remaining(), {"new": 5, "review": 1})

    def test_progress_is_saved_and_reloaded(self):
        s = self.session()
        pid = s.current.id
        s.rate(GOOD)
        reloaded = Progress(self.path)
        self.assertFalse(reloaded.state(pid).is_new)
        self.assertEqual(reloaded.daily["new"], 1)

    def test_undo_restores_everything(self):
        s = self.session()
        first, queue = s.current, list(s.queue)
        s.rate(GOOD)
        s.rate(AGAIN)
        self.assertTrue(s.undo())
        self.assertTrue(s.undo())
        self.assertFalse(s.undo())
        self.assertEqual(s.queue, queue)
        self.assertTrue(self.progress.state(first.id).is_new)
        self.assertEqual(Progress(self.path).daily["new"], 0)

    def test_add_new_skips_queued(self):
        s = self.session()
        self.assertEqual(s.add_new(10), 10)
        ids = [p.id for p in s.queue]
        self.assertEqual(len(ids), 15)
        self.assertEqual(len(set(ids)), 15)

    def test_daily_counters_reset(self):
        s = self.session()
        s.rate(GOOD)
        self.assertEqual(self.progress.counters(TODAY + timedelta(days=1))["new"], 0)

    def test_statistics(self):
        s = self.session()
        s.rate(GOOD)
        s.rate(AGAIN)
        stats = statistics(self.phrases, self.progress, TODAY)["B1"]
        self.assertEqual(stats, dict(total=30, new=28, learning=1, young=1, mature=0, due=1))


class RealDataTest(unittest.TestCase):
    def test_all_phrases_load(self):
        phrases = load_all()
        counts = Counter(p.level for p in phrases)
        expected = {"B1": 1000, "B2": 1500, "C1": 1500, "Wort-B1": 1000, "Wort-B2": 1000, "Wort-C1": 1000}
        self.assertEqual({level: counts[level] for level in expected}, expected)
        self.assertTrue(all(len(p.examples) == 3 for p in phrases))


if __name__ == "__main__":
    unittest.main()
