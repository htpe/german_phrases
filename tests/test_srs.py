import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from srs import AGAIN, EASY, GOOD, HARD, MIN_EASE, CardState, format_interval, review

TODAY = date(2026, 1, 1)


class ReviewTest(unittest.TestCase):
    def test_new_card_intervals(self):
        self.assertEqual(review(CardState(), AGAIN, TODAY).interval, 0)
        self.assertEqual(review(CardState(), HARD, TODAY).interval, 1)
        self.assertEqual(review(CardState(), GOOD, TODAY).interval, 1)
        self.assertEqual(review(CardState(), EASY, TODAY).interval, 4)

    def test_good_sequence_grows(self):
        state, intervals = CardState(), []
        for _ in range(5):
            state = review(state, GOOD, TODAY)
            intervals.append(state.interval)
        self.assertEqual(intervals[:3], [1, 6, 15])
        self.assertEqual(intervals, sorted(intervals))

    def test_due_date_and_new_flag(self):
        state = review(CardState(), EASY, TODAY)
        self.assertFalse(state.is_new)
        self.assertEqual(state.due, "2026-01-05")
        self.assertFalse(state.is_due(TODAY))
        self.assertTrue(state.is_due(date(2026, 1, 5)))

    def test_again_resets_and_counts_lapse(self):
        state = review(review(CardState(), GOOD, TODAY), GOOD, TODAY)
        forgotten = review(state, AGAIN, TODAY)
        self.assertEqual((forgotten.reps, forgotten.interval, forgotten.lapses), (0, 0, 1))
        self.assertTrue(forgotten.is_due(TODAY))
        self.assertAlmostEqual(forgotten.ease, state.ease - 0.2)

    def test_again_on_new_card_is_not_a_lapse(self):
        self.assertEqual(review(CardState(), AGAIN, TODAY).lapses, 0)

    def test_ease_has_floor(self):
        state = CardState()
        for _ in range(20):
            state = review(state, AGAIN, TODAY)
        self.assertEqual(state.ease, MIN_EASE)

    def test_hard_grows_slower_than_good_slower_than_easy(self):
        base = CardState(reps=3, interval=10, ease=2.5, due="2026-01-01", last_review="2025-12-22")
        hard, good, easy = (review(base, r, TODAY).interval for r in (HARD, GOOD, EASY))
        self.assertLess(hard, good)
        self.assertLess(good, easy)

    def test_invalid_rating(self):
        with self.assertRaises(ValueError):
            review(CardState(), 5, TODAY)

    def test_round_trip(self):
        state = review(CardState(), GOOD, TODAY)
        self.assertEqual(CardState.from_dict(state.to_dict()), state)

    def test_format_interval(self):
        self.assertEqual(format_interval(0), "now")
        self.assertEqual(format_interval(6), "6d")
        self.assertEqual(format_interval(60), "2mo")
        self.assertEqual(format_interval(730), "2y")


if __name__ == "__main__":
    unittest.main()
