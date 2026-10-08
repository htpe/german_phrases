"""Spaced-repetition scheduling (an SM-2 variant, as used by Anki-style apps).

Ratings: AGAIN (forgot), HARD, GOOD, EASY. Intervals are whole days.
"""
from dataclasses import asdict, dataclass
from datetime import date, timedelta

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
RATINGS = (AGAIN, HARD, GOOD, EASY)
RATING_NAMES = {AGAIN: "Again", HARD: "Hard", GOOD: "Good", EASY: "Easy"}

START_EASE = 2.5
MIN_EASE = 1.3
MAX_INTERVAL = 3650
MATURE_INTERVAL = 21  # days; cards at or above this count as "mature"


@dataclass
class CardState:
    reps: int = 0          # successful reviews in a row
    interval: int = 0      # current interval in days
    ease: float = START_EASE
    lapses: int = 0        # times forgotten after having been learned
    due: str = ""          # ISO date; "" means never studied (new)
    last_review: str = ""

    @property
    def is_new(self) -> bool:
        return not self.last_review

    def is_due(self, today: date) -> bool:
        return not self.is_new and date.fromisoformat(self.due) <= today

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CardState":
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in fields})


def next_interval(state: CardState, rating: int) -> int:
    """Interval in days the card would get for `rating` (0 = again today)."""
    if rating == AGAIN:
        return 0
    if state.reps == 0:
        interval = {HARD: 1, GOOD: 1, EASY: 4}[rating]
    elif state.reps == 1:
        interval = {HARD: 3, GOOD: 6, EASY: 8}[rating]
    else:
        factor = {HARD: 1.2, GOOD: state.ease, EASY: state.ease * 1.3}[rating]
        interval = max(state.interval + 1, round(state.interval * factor))
    return min(interval, MAX_INTERVAL)


def review(state: CardState, rating: int, today: date) -> CardState:
    """Return the new state after rating a card on `today`."""
    if rating not in RATINGS:
        raise ValueError(f"invalid rating {rating!r}")
    interval = next_interval(state, rating)
    ease, reps, lapses = state.ease, state.reps, state.lapses
    if rating == AGAIN:
        if reps > 0:
            lapses += 1
        reps = 0
        ease -= 0.2
    else:
        reps += 1
        ease += {HARD: -0.15, GOOD: 0.0, EASY: 0.15}[rating]
    return CardState(
        reps=reps,
        interval=interval,
        ease=round(max(MIN_EASE, ease), 2),
        lapses=lapses,
        due=(today + timedelta(days=interval)).isoformat(),
        last_review=today.isoformat(),
    )


def format_interval(days: int) -> str:
    if days == 0:
        return "now"
    if days < 30:
        return f"{days}d"
    if days < 365:
        return f"{days / 30:.1f}mo".replace(".0mo", "mo")
    return f"{days / 365:.1f}y".replace(".0y", "y")
