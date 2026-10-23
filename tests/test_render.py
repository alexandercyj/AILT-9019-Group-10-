"""Renderer behaviour at the edges: long values, word band, determinism."""

from __future__ import annotations

from labeldesk.grounding import check_citation_resolution, check_value_containment
from labeldesk.render import WORD_BAND, medium_variants, render_label
from labeldesk.text import words

BASE = {
    "catalogue_number": "TEST.1",
    "object_id": 1,
    "title": "Bowl",
    "object_date": "19th century",
    "medium": "Porcelain",
    "place_or_culture": "China",
    "credit_line": "Rogers Fund, 1920",
}


def test_short_record_is_padded_into_the_band():
    result = render_label(BASE)
    assert WORD_BAND[0] <= words(result["label"]) <= WORD_BAND[1]
    assert result["padding"], "a short label should be padded with carrier sentences"


def test_padding_sentences_add_no_facts():
    result = render_label(BASE)
    for sentence in result["padding"]:
        assert sentence in result["label"]


def test_long_medium_is_shortened_to_a_prefix():
    record = {
        **BASE,
        "medium": (
            "Clay; moulded frame and shaped supports glazed black; both faces of screen "
            "with ivory glaze, decorated with landscapes in black (Tokyo ware)"
        ),
    }
    variants = medium_variants(record["medium"])
    assert len(variants) > 1
    for variant in variants:
        assert record["medium"].startswith(variant)


def test_shortened_medium_still_resolves_as_a_citation():
    record = {
        **BASE,
        "medium": (
            "Clay; moulded frame and shaped supports glazed black; both faces of screen "
            "with ivory glaze, decorated with landscapes in black (Tokyo ware)"
        ),
    }
    result = render_label(record)
    assert WORD_BAND[0] <= words(result["label"]) <= WORD_BAND[1]
    assert check_citation_resolution(result["citations"], record)["passed"] is True
    assert check_value_containment(result["claims"], record)["passed"] is True


def test_a_very_long_medium_is_flagged_as_shortened():
    record = {**BASE, "medium": " ".join(f"material{i}" for i in range(60))}
    result = render_label(record)
    assert WORD_BAND[0] <= result["word_count"] <= WORD_BAND[1]
    assert result["shortened_medium"] is True
    assert check_citation_resolution(result["citations"], record)["passed"] is True


def test_render_is_pure():
    assert render_label(BASE) == render_label(BASE)
