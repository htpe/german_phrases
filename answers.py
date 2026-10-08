"""Check a typed answer against the expected phrase, tolerating small mistakes."""
import re
from difflib import SequenceMatcher

from srs import AGAIN, GOOD, HARD

# Placeholders learners may leave out when typing.
_OPTIONAL = re.compile(
    r"\b(etw|etwas|jdn|jemanden|jdm|jemandem|jds|jemandes|sich"
    r"|sth|sb|someone|somebody|something|oneself)\b\.?", re.I)
_UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def normalize(text: str) -> str:
    text = text.casefold()
    for k, v in _UMLAUTS.items():
        text = text.replace(k, v)
    text = _OPTIONAL.sub(" ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = " ".join(text.split())
    return text[3:] if text.startswith("to ") else text  # "to meet sth." == "meet"


def alternatives(expected: str) -> list[str]:
    """'to put sb. in the picture, to brief sb.' -> both variants."""
    parts = [p for p in re.split(r"[,;/]", expected) if p.strip()]
    return [expected, *parts] if len(parts) > 1 else [expected]


def check(typed: str, expected: str) -> tuple[float, int]:
    """Return (similarity 0..1, suggested rating)."""
    typed_n = normalize(typed)
    if not typed_n:
        return 0.0, AGAIN
    score = max(SequenceMatcher(None, typed_n, normalize(alt)).ratio()
                for alt in alternatives(expected))
    if score >= 0.95:
        return score, GOOD
    if score >= 0.8:
        return score, HARD
    return score, AGAIN
