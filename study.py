"""Study sessions: build the daily queue, apply ratings, undo, statistics."""
from dataclasses import dataclass
from datetime import date

from phrase_loader import Phrase
from progress import Progress
from srs import AGAIN, MATURE_INTERVAL, RATINGS, CardState, next_interval, review

AGAIN_GAP = 3  # a forgotten card comes back after this many other cards
MAX_LOGGED_SECONDS = 60  # cap per card so a break doesn't count as study time


@dataclass
class _UndoStep:
    phrase_id: str
    old_state: CardState | None
    queue: list[Phrase]
    daily: dict


class StudySession:
    """Spaced-repetition session: due reviews first, then today's new phrases."""

    def __init__(self, phrases: list[Phrase], progress: Progress, today: date | None = None):
        self.phrases = phrases
        self.progress = progress
        self.today = today or date.today()
        self._undo: list[_UndoStep] = []
        self.rated: list[tuple[Phrase, int]] = []  # this session's ratings, oldest first

        due = [p for p in phrases if progress.state(p.id).is_due(self.today)]
        due.sort(key=lambda p: progress.state(p.id).due)
        new_left = max(0, progress.settings["new_per_day"] - progress.counters(self.today)["new"])
        self.queue: list[Phrase] = due + self._new_phrases(new_left)

    def _new_phrases(self, limit: int, queued: set[str] = frozenset()) -> list[Phrase]:
        fresh = [p for p in self.phrases
                 if p.id not in queued and self.progress.state(p.id).is_new]
        return fresh[:limit]

    @property
    def current(self) -> Phrase | None:
        return self.queue[0] if self.queue else None

    def preview(self) -> dict[int, int]:
        """Interval in days each rating would give the current card."""
        state = self.progress.state(self.current.id)
        return {r: next_interval(state, r) for r in RATINGS}

    def rate(self, rating: int, seconds: float = 0) -> None:
        phrase = self.current
        if phrase is None:
            raise RuntimeError("no card to rate")
        old = self.progress.cards.get(phrase.id)
        daily = self.progress.counters(self.today)
        self._undo.append(_UndoStep(phrase.id, old, list(self.queue), dict(daily)))

        state = old or CardState()
        daily["new" if state.is_new else "reviews"] += 1
        self.progress.cards[phrase.id] = review(state, rating, self.today)
        self.progress.log.append([self.today.isoformat(), phrase.id, rating,
                                  round(min(seconds, MAX_LOGGED_SECONDS), 1), int(state.is_new)])
        self.rated.append((phrase, rating))
        self.queue.pop(0)
        if rating == AGAIN:
            self.queue.insert(min(AGAIN_GAP, len(self.queue)), phrase)
        self.progress.save()

    def undo(self) -> bool:
        if not self._undo:
            return False
        step = self._undo.pop()
        if step.old_state is None:
            self.progress.cards.pop(step.phrase_id, None)
        else:
            self.progress.cards[step.phrase_id] = step.old_state
        self.queue = step.queue
        self.progress.daily = step.daily
        if self.progress.log and self.progress.log[-1][1] == step.phrase_id:
            self.progress.log.pop()
        self.rated.pop()
        self.progress.save()
        return True

    def skip(self) -> bool:
        """Move the current card to the end of the queue."""
        if len(self.queue) < 2:
            return False
        self.queue.append(self.queue.pop(0))
        return True

    def add_new(self, count: int) -> int:
        """Queue up to `count` extra new phrases beyond today's limit."""
        extra = self._new_phrases(count, {p.id for p in self.queue})
        self.queue.extend(extra)
        return len(extra)

    def remaining(self) -> dict[str, int]:
        new = sum(1 for p in self.queue if self.progress.state(p.id).is_new)
        return {"new": new, "review": len(self.queue) - new}


class PracticeSession:
    """Drill a fixed list without touching the schedule or the learning log.

    "Again" brings a card back later; any other rating removes it from the round.
    """

    def __init__(self, phrases: list[Phrase]):
        self.queue = list(phrases)
        self.rated: list[tuple[Phrase, int]] = []
        self._undo: list[list[Phrase]] = []
        self.total = len(phrases)

    @property
    def current(self) -> Phrase | None:
        return self.queue[0] if self.queue else None

    def preview(self) -> dict[int, int]:
        return {r: 0 for r in RATINGS}

    def rate(self, rating: int, seconds: float = 0) -> None:
        phrase = self.current
        if phrase is None:
            raise RuntimeError("no card to rate")
        self._undo.append(list(self.queue))
        self.rated.append((phrase, rating))
        self.queue.pop(0)
        if rating == AGAIN:
            self.queue.insert(min(AGAIN_GAP, len(self.queue)), phrase)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self.queue = self._undo.pop()
        self.rated.pop()
        return True

    def skip(self) -> bool:
        if len(self.queue) < 2:
            return False
        self.queue.append(self.queue.pop(0))
        return True

    def remaining(self) -> dict[str, int]:
        return {"new": 0, "review": len(self.queue)}


def todays_phrases(phrases: list[Phrase], progress: Progress,
                   today: date | None = None) -> list[Phrase]:
    """All phrases of the day: those already reviewed today (in review order),
    then those still waiting in today's queue (due reviews and today's new phrases)."""
    today = today or date.today()
    allowed = {p.id: p for p in phrases}
    day = today.isoformat()
    reviewed = dict.fromkeys(pid for d, pid, *_ in progress.log if d == day and pid in allowed)
    waiting = [p for p in StudySession(phrases, progress, today).queue if p.id not in reviewed]
    return [allowed[pid] for pid in reviewed] + waiting


def statistics(phrases: list[Phrase], progress: Progress, today: date | None = None) -> dict:
    """Card counts per level: new / learning / young / mature / due today."""
    today = today or date.today()
    stats: dict[str, dict[str, int]] = {}
    for p in phrases:
        row = stats.setdefault(p.level, dict(total=0, new=0, learning=0, young=0, mature=0, due=0))
        s = progress.state(p.id)
        row["total"] += 1
        if s.is_new:
            row["new"] += 1
            continue
        if s.reps == 0:
            row["learning"] += 1
        elif s.interval >= MATURE_INTERVAL:
            row["mature"] += 1
        else:
            row["young"] += 1
        if s.is_due(today):
            row["due"] += 1
    return stats
