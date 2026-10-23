"""Text primitives shared by the renderer and the grounding check.

The grounding check compares a claim with the field value it cites. To do that
without a parser or a model, both sides are reduced to lower-case word and digit
tokens. Everything the renderer is allowed to add on top of a field value lives
in CARRIER_WORDS: function words, field names, and the verbs of the fixed
templates. Any other word in a claim has to come from the cited value, which is
what makes an invented fact detectable.

Hedges are handled separately. A hedge may be reworded ("ca." -> "around") but
may never disappear, so hedges are matched by family rather than as bare tokens.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z]+|\d+")

# Words a claim may use without them counting as a fact. Kept deliberately small
# and reviewed by hand: function words, field names, and the verbs of the fixed
# templates.
CARRIER_WORDS: frozenset[str] = frozenset(
    """
    a an the this that these those it its is are was were be been being
    of in on at to for from by with as and but not no
    object objects catalogue record records field fields
    titled title dates dated recorded given reads read
    made produced created
    medium place culture credit line
    draft drafting aid curator review official museum
    every sentence above restates one fact outside has added
    """.split()
)

# Uncertainty the museum itself records, grouped by meaning. A claim may use any
# member of the family its cited value uses, but may not drop the family: the
# record's "probably Iran" must not become a flat "Iran".
HEDGE_FAMILIES: dict[str, frozenset[str]] = {
    "approximate": frozenset({"ca", "circa", "around", "about", "approximately", "approx"}),
    "probable": frozenset({"probably", "presumably", "likely"}),
    "possible": frozenset({"possibly", "perhaps", "maybe", "apparently"}),
    "disjunction": frozenset({"or"}),
}
HEDGE_TOKENS: frozenset[str] = frozenset().union(*HEDGE_FAMILIES.values())

SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")


def tokenize(text: str) -> list[str]:
    """Lower-case word and digit tokens. Hyphens and dashes split words."""
    return TOKEN_RE.findall(text.lower())


def content_tokens(text: str) -> list[str]:
    """Tokens that carry a fact.

    Carrier words and hedges are excluded: hedges are validated by family in the
    grounding check instead, so "probably made in Iran" is not rejected for the
    word "probably".
    """
    return [
        token
        for token in tokenize(text)
        if token not in CARRIER_WORDS and token not in HEDGE_TOKENS
    ]


def numbers(text: str) -> set[str]:
    """Digit strings in a text: '1713–22' -> {'1713', '22'}."""
    return set(re.findall(r"\d+", text))


def hedges(text: str) -> set[str]:
    """Hedge families present in a text, plus 'question_mark' for the '(?)' marker."""
    tokens = set(tokenize(text))
    found = {name for name, family in HEDGE_FAMILIES.items() if tokens & family}
    if "?" in text:
        found.add("question_mark")
    return found


def normalise(text: str) -> str:
    """Casefold and collapse whitespace, for substring comparison."""
    return " ".join(text.split()).casefold()


def words(text: str) -> int:
    """Word count as a reader counts it: whitespace-separated runs."""
    return len(text.split())


def sentences(text: str) -> list[str]:
    """Split on sentence-final punctuation, keeping the punctuation."""
    return [part.strip() for part in SENTENCE_RE.findall(text) if part.strip()]


def average_sentence_length(text: str) -> float:
    parts = sentences(text)
    if not parts:
        return 0.0
    return round(sum(words(part) for part in parts) / len(parts), 2)
