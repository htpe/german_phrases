"""Per-day learning progress from the review log: summaries, day highlights, streaks."""
from dataclasses import dataclass, field
from datetime import date, timedelta

from srs import AGAIN, EASY, GOOD, HARD

# Day kinds, shown as calendar highlights.
GOOD_DAY = "good"        # daily goal reached and >= GOOD_ACCURACY recalled
STUDIED = "studied"      # studied, but not a good or hard day
HARD_DAY = "hard"        # many phrases forgotten (< HARD_ACCURACY recalled)
MISSED = "missed"        # forgot to study (a past day with no reviews)
NO_DATA = "none"         # before the first study day, or in the future

GOOD_ACCURACY = 0.85
HARD_ACCURACY = 0.70
MIN_HARD_RATINGS = 10   # a few unlucky ratings don't make a hard day


@dataclass
class DaySummary:
    day: date
    ratings: dict[int, int] = field(default_factory=lambda: {AGAIN: 0, HARD: 0, GOOD: 0, EASY: 0})
    new: int = 0
    seconds: float = 0.0
    reviews: list[tuple[str, int]] = field(default_factory=list)  # (phrase_id, rating)

    @property
    def total(self) -> int:
        return sum(self.ratings.values())

    @property
    def forgotten(self) -> int:
        return self.ratings[AGAIN]

    @property
    def recalled(self) -> int:
        return self.total - self.forgotten

    @property
    def accuracy(self) -> float:
        return self.recalled / self.total if self.total else 0.0

    @property
    def forgotten_ids(self) -> list[str]:
        return sorted({pid for pid, r in self.reviews if r == AGAIN})


def summarize(log: list[list]) -> dict[date, DaySummary]:
    days: dict[date, DaySummary] = {}
    for day_iso, pid, rating, seconds, was_new in log:
        day = date.fromisoformat(day_iso)
        s = days.setdefault(day, DaySummary(day))
        s.ratings[rating] += 1
        s.new += was_new
        s.seconds += seconds
        s.reviews.append((pid, rating))
    return days


def classify(day: date, days: dict[date, DaySummary], goal: int, today: date) -> str:
    s = days.get(day)
    if s and s.total:
        if s.accuracy < HARD_ACCURACY and s.total >= MIN_HARD_RATINGS:
            return HARD_DAY
        if s.total >= goal and s.accuracy >= GOOD_ACCURACY:
            return GOOD_DAY
        return STUDIED
    first = min(days) if days else None
    if first is None or day < first or day >= today:
        return NO_DATA  # today is not "missed" yet: there is still time to study
    return MISSED


def streaks(days: dict[date, DaySummary], today: date) -> tuple[int, int]:
    """(current streak, longest streak) of consecutive study days."""
    studied = {d for d, s in days.items() if s.total}
    longest = run = 0
    prev = None
    for d in sorted(studied):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    current = 0
    d = today if today in studied else today - timedelta(days=1)
    while d in studied:
        current += 1
        d -= timedelta(days=1)
    return current, longest


def last_n_days(days: dict[date, DaySummary], today: date, n: int) -> list[DaySummary]:
    return [days.get(d) or DaySummary(d) for d in (today - timedelta(days=i) for i in range(n - 1, -1, -1))]
