"""The import path: the route for records a person may hold but a crawler may not.

The British Museum and the Palace Museum are refused as automated sources. That
refusal is only honest if there is somewhere else for their records to go, so this
tool exists: a person types five fields into a CSV, names the licence they are
asserting, says why they may hold the records, and the corpus is registered with
that assertion attached.

The tests below are mostly about what the tool *refuses*. A CSV importer that
accepts a misaligned row is worse than no importer, because the resulting corpus
looks fine and cites the wrong field.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import import_records as importer  # noqa: E402

from labeldesk.corpus import load_corpus  # noqa: E402
from labeldesk.pipeline import draft  # noqa: E402
from labeldesk.sources import ai_input_allowed, provenance  # noqa: E402

HEADER = "catalogue_number,title,object_date,medium,place_or_culture,credit_line\n"
GOOD_ROW = '"1890,0122.1",Ritual bronze vessel,ca. 1100-1050 BC,Bronze,"China, Shang dynasty",Gift of a donor\n'


def _csv(tmp_name: str, body: str) -> Path:
    target = Path(__file__).with_name(tmp_name)
    target.write_text(HEADER + body, encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# reading the input
# --------------------------------------------------------------------------- #


def test_a_well_formed_csv_reads_cleanly():
    target = _csv("_tmp_import_ok.csv", GOOD_ROW)
    try:
        rows, missing, misaligned = importer.read_csv(target)
    finally:
        target.unlink()
    assert missing == []
    assert misaligned == []
    assert rows[0]["catalogue_number"] == "1890,0122.1"
    assert rows[0]["credit_line"] == "Gift of a donor"


def test_missing_columns_are_named():
    target = Path(__file__).with_name("_tmp_import_short.csv")
    target.write_text("catalogue_number,title\n1,A thing\n", encoding="utf-8")
    try:
        _rows, missing, _mis = importer.read_csv(target)
    finally:
        target.unlink()
    assert "object_date" in missing
    assert "credit_line" in missing


def test_an_unquoted_comma_is_refused_not_shifted():
    """The failure mode that matters: csv does not error, it misaligns."""
    target = _csv("_tmp_import_shift.csv", "1,A thing,1900,Bronze,China,Gift of X, extra\n")
    try:
        _rows, _missing, misaligned = importer.read_csv(target)
    finally:
        target.unlink()
    assert misaligned == [2], "the extra field must be reported, not dropped"


# --------------------------------------------------------------------------- #
# validating the input
# --------------------------------------------------------------------------- #


def test_a_blank_required_field_is_reported_with_the_line():
    rows = [
        {
            "catalogue_number": "1",
            "title": "A thing",
            "object_date": "",
            "medium": "Bronze",
            "place_or_culture": "China",
            "credit_line": "Gift",
        }
    ]
    _records, problems = importer.validate(rows)
    assert problems and "object_date" in problems[0]


def test_a_duplicate_catalogue_number_is_reported():
    row = {
        "catalogue_number": "1",
        "title": "A thing",
        "object_date": "1900",
        "medium": "Bronze",
        "place_or_culture": "China",
        "credit_line": "Gift",
    }
    _records, problems = importer.validate([row, dict(row)])
    assert any("duplicate" in problem for problem in problems)


def test_object_id_falls_back_to_the_catalogue_number():
    rows, _problems = importer.validate(
        [
            {
                "catalogue_number": "1890,0122.1",
                "title": "A thing",
                "object_date": "1900",
                "medium": "Bronze",
                "place_or_culture": "China",
                "credit_line": "Gift",
            }
        ]
    )
    assert rows[0]["object_id"] == "1890,0122.1"


def test_imported_records_are_not_marked_public_domain():
    """The importer asserts a licence. That is not the same as a PD mark."""
    rows, _ = importer.validate(
        [
            {
                "catalogue_number": "1",
                "title": "A thing",
                "object_date": "1900",
                "medium": "Bronze",
                "place_or_culture": "China",
                "credit_line": "Gift",
            }
        ]
    )
    assert rows[0]["is_public_domain"] is False


# --------------------------------------------------------------------------- #
# the two files the tool writes
# --------------------------------------------------------------------------- #


class Args:
    def __init__(self, **overrides):
        self.id = "demo-import"
        self.name = "Demo Import (synthetic)"
        self.license = "CC0-1.0"
        self.license_url = None
        self.basis = "Synthetic records for a test."
        self.alias = "demo"
        self.homepage = None
        self.ai_input = False
        self.redistribute = False
        self.no_attribution = False
        self.__dict__.update(overrides)


def _records():
    rows, problems = importer.validate(
        [
            {
                "catalogue_number": "1",
                "title": "A thing",
                "object_date": "ca. 1900",
                "medium": "Bronze",
                "place_or_culture": "China",
                "credit_line": "Gift of a donor",
            }
        ]
    )
    assert not problems
    return rows


def test_corpus_uses_the_identity_field_map():
    """The CSV columns are already the corpus's own names, so no mapping is needed."""
    corpus = importer.build_corpus(
        _records(), name="labeldesk-demo-corpus", source="Demo", license_id="CC0-1.0"
    )
    mapping = corpus["corpus"]["field_map"]
    assert all(key == value for key, value in mapping.items())
    assert corpus["corpus"]["record_count"] == 1


def test_source_defaults_to_refusing_the_model():
    source = importer.build_source(Args(), "labeldesk-demo-corpus", "data/x.json", 1)
    assert source["policy"]["ai_input"] is False
    assert source["policy"]["record_source"] is True
    assert source["decision"]["status"] == "imported"
    assert "Synthetic records for a test." in source["decision"]["reason"]


def test_source_records_that_nothing_was_crawled():
    source = importer.build_source(Args(), "labeldesk-demo-corpus", "data/x.json", 1)
    assert source["robots"]["verdict"] == "not_applicable"
    assert source["robots"]["url"] is None
    assert "not crawled" in source["robots"]["notes"]


def test_opt_in_flips_ai_input():
    source = importer.build_source(Args(ai_input=True), "labeldesk-demo-corpus", "data/x.json", 1)
    assert source["policy"]["ai_input"] is True


def test_the_basis_is_kept_verbatim_in_the_reason():
    """A refusal or an admission is only auditable if the reason travels with it."""
    basis = "Collection records copied by a curator with collection access."
    source = importer.build_source(Args(basis=basis), "c", "f", 3)
    assert basis in source["decision"]["reason"]
    assert "3 records" in source["decision"]["reason"]


# --------------------------------------------------------------------------- #
# an imported corpus behaves like any other, with one difference
# --------------------------------------------------------------------------- #


def _registered(tmp_name: str, ai_input: bool):
    """Write a corpus and a one-source register next to this test file."""
    records = _records()
    corpus_payload = importer.build_corpus(
        records, name="labeldesk-demo-corpus", source="Demo", license_id="CC0-1.0"
    )
    corpus_path = Path(__file__).with_name(tmp_name)
    corpus_path.write_text(json.dumps(corpus_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    register_path = Path(__file__).with_name(tmp_name.replace(".json", "_sources.json"))
    register_path.write_text(
        json.dumps(
            {"register": {"version": "1.0.0"}, "sources": [
                importer.build_source(Args(ai_input=ai_input), "labeldesk-demo-corpus", tmp_name, 1)
            ]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return corpus_path, register_path


def test_an_imported_corpus_drafts_cleanly():
    corpus_path, register_path = _registered("_tmp_demo_corpus.json", ai_input=False)
    try:
        corpus = load_corpus(corpus_path)
        result = draft(corpus, "1")
        assert result["status"] == "drafted"
        assert result["checks"]["passed"] is True
        assert "ca. 1900" in result["label"]
    finally:
        corpus_path.unlink(missing_ok=True)
        register_path.unlink(missing_ok=True)


def test_an_imported_corpus_refuses_the_model_unless_it_opted_in():
    corpus_path, register_path = _registered("_tmp_demo_corpus.json", ai_input=False)
    try:
        corpus = load_corpus(corpus_path)
        allowed, source, _policy = ai_input_allowed(corpus, register_path)
        assert allowed is False
        assert source["decision"]["status"] == "imported"
        prov = provenance(corpus, register_path)
        assert prov["registered"] is True
        assert prov["ai_input"] is False
    finally:
        corpus_path.unlink(missing_ok=True)
        register_path.unlink(missing_ok=True)


def test_an_imported_corpus_that_opted_in_may_use_the_model():
    corpus_path, register_path = _registered("_tmp_demo_corpus.json", ai_input=True)
    try:
        corpus = load_corpus(corpus_path)
        allowed, _source, _policy = ai_input_allowed(corpus, register_path)
        assert allowed is True
    finally:
        corpus_path.unlink(missing_ok=True)
        register_path.unlink(missing_ok=True)


def test_the_pipeline_consults_the_shipped_register_not_a_private_one():
    """Registration only counts when it is in the repository's own register.

    This is deliberate. A corpus that names a source nobody can look up is exactly
    the situation the register exists to prevent, so `draft()` does not accept a
    register path: there is one register, and it is in version control.
    """
    corpus_path, register_path = _registered("_tmp_demo_corpus.json", ai_input=True)
    try:
        corpus = load_corpus(corpus_path)
        result = draft(corpus, "1", llm="replay")
        assert result["llm"]["reason"] == "source_policy"
        assert result["provenance"]["registered"] is False
    finally:
        corpus_path.unlink(missing_ok=True)
        register_path.unlink(missing_ok=True)


def test_the_tools_slugify_keeps_ids_addressable():
    assert importer.slugify("BM Import 2026") == "bm-import-2026"
    assert importer.slugify("  Palace Museum / 故宫 ") == "palace-museum"
