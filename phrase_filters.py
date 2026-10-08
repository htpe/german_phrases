"""Select, search and sort phrases for the list view and practice rounds."""
from datetime import date

from phrase_loader import Phrase
from progress import Progress

DIFFICULT_LAPSES = 3  # forgotten this many times = a "difficult" phrase (leech)

FILTERS = {
    "learned": "Learned (studied at least once)",
    "to_learn": "To be learned (new)",
    "due": "Due for review today",
    "forgotten": "Forgotten at least once",
    "difficult": f"Difficult (forgotten {DIFFICULT_LAPSES}+ times)",
    "starred": "Starred",
    "mature": "Well known (interval 21+ days)",
    "all": "All phrases",
}
SORTS = {
    "id": "Original order",
    "due": "Next review date",
    "lapses": "Most forgotten first",
    "ease": "Hardest first (lowest ease)",
    "recent": "Most recently reviewed",
    "alpha": "German A-Z",
}


def was_forgotten(state) -> bool:
    """Forgotten after learning it, or failed on the first try and not yet recalled."""
    return state.lapses > 0 or (not state.is_new and state.reps == 0)


def matches(p: Phrase, kind: str, progress: Progress, today: date) -> bool:
    s = progress.state(p.id)
    return {
        "learned": lambda: not s.is_new,
        "to_learn": lambda: s.is_new,
        "due": lambda: s.is_due(today),
        "forgotten": lambda: was_forgotten(s),
        "difficult": lambda: s.lapses >= DIFFICULT_LAPSES,
        "starred": lambda: p.id in progress.starred,
        "mature": lambda: s.interval >= 21,
        "all": lambda: True,
    }[kind]()


def search_text(p: Phrase) -> str:
    examples = " ".join(f"{de} {en}" for de, en in p.examples)
    return f"{p.id} {p.german} {p.english} {p.chinese} {examples}".casefold()


def select(phrases: list[Phrase], progress: Progress, kind: str = "all", query: str = "",
           sort: str = "id", limit: int | None = None, today: date | None = None) -> list[Phrase]:
    today = today or date.today()
    query = query.casefold().strip()
    result = [p for p in phrases
              if matches(p, kind, progress, today) and (not query or query in search_text(p))]
    state = progress.state
    keys = {
        "id": None,
        "due": lambda p: state(p.id).due or "9999",
        "lapses": lambda p: -state(p.id).lapses,
        "ease": lambda p: state(p.id).ease,
        "recent": lambda p: state(p.id).last_review,
        "alpha": lambda p: p.german.casefold(),
    }
    if keys[sort]:
        result.sort(key=keys[sort], reverse=(sort == "recent"))
    return result[:limit] if limit else result
