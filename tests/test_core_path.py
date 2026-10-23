"""The core path: one record in, a cited label out, every claim checked."""

from __future__ import annotations

import pytest

from labeldesk import draft, load_corpus
from labeldesk.text import words


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def test_draft_returns_a_label_with_five_claims(corpus):
    result = draft(corpus, "14.40.377")
    assert result["status"] == "drafted"
    assert len(result["claims"]) == 5
    assert [claim["source_field"] for claim in result["claims"]] == [
        "title",
        "object_date",
        "medium",
        "place_or_culture",
        "credit_line",
    ]


def test_label_restates_the_record_and_passes_every_check(corpus):
    result = draft(corpus, "14.40.377")
    label = result["label"]
    assert "Vase" in label
    assert "1713–22" in label
    assert "Bequest of Benjamin Altman, 1913" in label
    assert result["checks"]["passed"] is True
    assert result["checks"]["claim_precision"] == 1.0
    assert result["checks"]["citation_resolution_rate"] == 1.0


def test_label_sits_in_the_sixty_to_eighty_word_band(corpus):
    for number in corpus.catalogue_numbers():
        result = draft(corpus, number)
        if result["status"] != "drafted":
            continue
        assert 60 <= words(result["label"]) <= 80, number
        assert result["checks"]["average_sentence_length"] < 20, number


def test_label_always_carries_the_review_notice(corpus):
    result = draft(corpus, "20.45")
    assert result["label"].endswith(result["notice"])
    assert "not an official record" in result["notice"]


def test_every_claim_cites_a_field_and_an_exact_slice(corpus):
    result = draft(corpus, "62.173.7")
    record = result["record"]
    for claim in result["claims"]:
        field = claim["source_field"]
        assert claim["value_span"]
        assert claim["value_span"] in record[field]
        assert claim["text"] in result["label"]


def test_rendering_is_deterministic(corpus):
    first = draft(corpus, "1999.247.1")
    second = draft(corpus, "1999.247.1")
    assert first["label"] == second["label"]
    assert first["claims"] == second["claims"]


def test_hedged_date_keeps_its_hedge(corpus):
    result = draft(corpus, "36.120.655")
    assert "ca. 1740" in result["label"]
    assert result["checks"]["passed"] is True


def test_doubt_marker_is_reproduced(corpus):
    result = draft(corpus, "2013.872")
    assert "late 18th century (?)" in result["label"]


def test_disjunctive_culture_is_not_resolved(corpus):
    result = draft(corpus, "67.182.1")
    assert "Old Assyrian Trading Colony or Hittite" in result["label"]
