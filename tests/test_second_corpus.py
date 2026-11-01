"""The second department's corpus, through the same pipeline and no new code.

The should-have item in the proposal is "a second department's corpus, to show the
pipeline is data-agnostic". These tests are what that claim means in practice:
the same package, the same four checks, a different museum department whose records
put the place in a different API field. Nothing in labeldesk/ was changed to make
this work — the field map lives in the corpus file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labeldesk import load_corpus
from labeldesk.corpus import REQUIRED_FIELDS, file_checksum
from labeldesk.pipeline import draft

ROOT = Path(__file__).resolve().parents[1]
EGYPTIAN = ROOT / "data" / "frozen_corpus_egyptian.json"
PRIMARY = ROOT / "data" / "frozen_corpus.json"


@pytest.fixture(scope="module")
def egyptian():
    return load_corpus(EGYPTIAN)


@pytest.fixture(scope="module")
def primary():
    return load_corpus(PRIMARY)


def test_corpus_loads_with_its_own_metadata(egyptian):
    assert len(egyptian) == 10
    assert egyptian.meta["name"] == "labeldesk-egyptian-corpus"
    assert egyptian.meta["record_count"] == 10
    assert egyptian.meta["license"] == "CC0 1.0 (public domain)"


def test_corpus_checksum_is_recorded_and_matches(egyptian):
    sidecar = EGYPTIAN.with_suffix(".sha256")
    assert sidecar.exists(), "a frozen corpus ships with its checksum"
    recorded = sidecar.read_text(encoding="utf-8").split()[0]
    assert recorded == file_checksum(EGYPTIAN)
    assert recorded == egyptian.checksum


def test_same_required_fields_as_the_primary_corpus(egyptian, primary):
    assert tuple(egyptian.meta["required_fields"]) == REQUIRED_FIELDS
    assert tuple(primary.meta["required_fields"]) == REQUIRED_FIELDS


def test_the_field_map_differs_because_the_department_differs(egyptian, primary):
    """This is the data-agnostic claim: the mapping is data, not code."""
    assert primary.meta["field_map"]["place_or_culture"] == "culture"
    assert egyptian.meta["field_map"]["place_or_culture"] == ["country", "culture"]
    assert {record["place_or_culture"] for record in egyptian.records} == {"Egypt"}


def test_every_record_drafts_or_refuses_cleanly(egyptian):
    for record in egyptian.records:
        result = draft(egyptian, record["catalogue_number"])
        assert result["status"] in ("drafted", "refused")
        if result["status"] == "drafted":
            assert result["checks"]["passed"] is True, record["catalogue_number"]
            assert 60 <= result["word_count"] <= 80
            assert len(result["claims"]) == 5
            assert result["checks"]["claim_precision"] == 1.0
            assert result["checks"]["citation_resolution_rate"] == 1.0


def test_a_catalogue_number_from_the_other_corpus_is_out_of_corpus(egyptian):
    result = draft(egyptian, "14.40.377")
    assert result["status"] == "refused"
    assert result["reason"] == "out_of_corpus"
    assert result["label"] is None


def test_the_doubt_marker_survives_on_this_data(egyptian):
    result = draft(egyptian, "26.7.1460")
    assert result["status"] == "drafted"
    assert "(?)" in result["label"]
    assert "or armlet" in result["label"]
    assert result["checks"]["passed"] is True


def test_the_medium_layer_is_used_when_values_are_short(egyptian):
    """Egyptian records have one-word media, so the framing sentences carry the band."""
    result = draft(egyptian, "29.3.1")
    assert result["record"]["medium"] == "Granite"
    assert result["padding"], "a short body must be completed with framing sentences"
    assert result["checks"]["readability"]["passed"] is True


def test_the_same_pipeline_serves_both_corpora(primary, egyptian):
    """One function, two data sets, identical result shape."""
    left = draft(primary, "14.40.377")
    right = draft(egyptian, "29.3.1")
    assert set(left) == set(right)
    assert set(left["checks"]) == set(right["checks"])
    assert left["record"]["department"] != right["record"]["department"]


def test_corpus_files_are_json_and_carry_no_personal_data(egyptian):
    payload = json.loads(EGYPTIAN.read_text(encoding="utf-8"))
    assert payload["corpus"]["license"].startswith("CC0")
    forbidden = {"email", "address", "phone", "donor_contact", "birth"}
    for record in payload["records"]:
        assert not (forbidden & set(record))
