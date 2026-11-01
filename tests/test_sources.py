"""The source register: every shipped corpus is accounted for, and policy bites.

Two kinds of test here. The first kind checks the register against the repository:
every corpus file on disk must be listed, and every listed file must exist. That
is the test that stops a new corpus from arriving without its licence.

The second kind checks that the policy is *enforced* rather than documented. It is
easy to write a JSON file full of good intentions and never read it; these tests
fail if the pipeline stops asking.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labeldesk.corpus import ROOT, load_corpus
from labeldesk.pipeline import draft
from labeldesk.sources import (
    REGISTER_PATH,
    UNREGISTERED_POLICY,
    ai_input_allowed,
    aliases,
    format_table,
    get_source,
    load_register,
    policy_for_corpus,
    provenance,
    resolve_corpus,
    source_for_corpus_file,
    source_for_corpus_name,
    sources,
)

DATA = ROOT / "data"


# --------------------------------------------------------------------------- #
# the register describes the repository
# --------------------------------------------------------------------------- #


def test_register_parses_and_has_sources():
    payload = load_register()
    assert payload["register"]["version"]
    assert len(payload["sources"]) >= 5


def test_every_shipped_corpus_is_registered():
    """A corpus file that no source claims has no licence on file."""
    shipped = sorted(DATA.glob("frozen_corpus*.json"))
    assert shipped, "no corpus files found; the test would pass vacuously"
    unregistered = [
        path.name for path in shipped if source_for_corpus_file(path) is None
    ]
    assert not unregistered, f"corpus files with no registered source: {unregistered}"


def test_every_registered_corpus_file_exists():
    """The other direction: the register must not name files that are gone."""
    missing = [
        corpus["file"]
        for source in sources()
        for corpus in source.get("corpora", [])
        if not (ROOT / corpus["file"]).exists()
    ]
    assert not missing, f"register names files that do not exist: {missing}"


def test_registered_name_matches_the_file():
    """`corpora[].name` must equal the corpus file's own `meta.name`.

    The lookup is by name, so a rename that updates one side and not the other
    would silently drop the corpus back to the unregistered default.
    """
    for source in sources():
        for entry in source.get("corpora", []):
            corpus = load_corpus(ROOT / entry["file"])
            assert corpus.meta["name"] == entry["name"], entry["file"]


def test_source_ids_are_unique():
    ids = [source["id"] for source in sources()]
    assert len(ids) == len(set(ids))


def test_every_source_has_the_four_required_blocks():
    for source in sources():
        for key in ("id", "name", "robots", "license", "policy", "decision"):
            assert key in source, f"{source.get('id')} is missing {key}"
        for key in ("verdict", "http_status", "checked"):
            assert key in source["robots"], f"{source['id']}.robots is missing {key}"
        assert source["decision"]["status"] in {
            "admitted",
            "refused",
            "deferred",
            "reference_only",
            "admitted_not_frozen",
            "imported",
        }
        assert source["decision"]["reason"].strip(), f"{source['id']} has no reason"


def test_a_refusal_cannot_be_used_as_a_record_source():
    """`record_source: false` and an admitted decision would be a contradiction."""
    for source in sources():
        if source["policy"].get("record_source"):
            continue
        assert source["decision"]["status"] != "admitted", source["id"]


def test_refused_sources_have_no_corpora():
    for source in sources():
        if source["decision"]["status"] == "refused":
            assert source.get("corpora") == [], source["id"]


# --------------------------------------------------------------------------- #
# lookup
# --------------------------------------------------------------------------- #


def test_get_source_returns_none_for_unknown():
    assert get_source("no-such-museum") is None


def test_source_for_corpus_name_is_the_inverse_of_the_register():
    for source in sources():
        for entry in source.get("corpora", []):
            assert source_for_corpus_name(entry["name"])["id"] == source["id"]


def test_aliases_cover_every_registered_corpus():
    table = aliases()
    count = sum(len(source.get("corpora", [])) for source in sources())
    assert len(table) == count
    for alias, path in table.items():
        assert alias and path.exists(), alias


def test_resolve_corpus_accepts_an_alias():
    assert resolve_corpus("cleveland").name == "frozen_corpus_cleveland.json"
    assert resolve_corpus("primary").name == "frozen_corpus.json"


def test_resolve_corpus_accepts_a_path():
    target = DATA / "frozen_corpus.json"
    assert resolve_corpus(str(target)) == target


def test_resolve_corpus_passes_none_through():
    assert resolve_corpus(None) is None


def test_unknown_alias_raises_rather_than_falling_back():
    """Silently reading the default corpus would answer with the wrong museum."""
    with pytest.raises(ValueError) as error:
        resolve_corpus("louvre")
    message = str(error.value)
    assert "louvre" in message
    assert "primary" in message  # the error lists what is valid


# --------------------------------------------------------------------------- #
# policy, and whether the pipeline reads it
# --------------------------------------------------------------------------- #


def test_shipped_corpora_permit_ai_input():
    for alias in ("primary", "egyptian", "cleveland"):
        corpus = load_corpus(resolve_corpus(alias))
        allowed, source, policy = ai_input_allowed(corpus)
        assert allowed, alias
        assert source is not None
        assert policy["ai_input"] is True


def test_unregistered_corpus_gets_the_safe_default():
    corpus = load_corpus(resolve_corpus("primary"))
    fake = type(corpus)(meta={**corpus.meta, "name": "not-in-the-register"}, records=corpus.records, path=corpus.path)
    source, policy = policy_for_corpus(fake)
    assert source is None
    assert policy == UNREGISTERED_POLICY
    assert policy["ai_input"] is False


def test_unregistered_provenance_does_not_echo_the_corpus_licence():
    corpus = load_corpus(resolve_corpus("primary"))
    fake = type(corpus)(meta={**corpus.meta, "name": "not-in-the-register"}, records=corpus.records, path=corpus.path)
    prov = provenance(fake)
    assert prov["registered"] is False
    assert prov["license"] is None, "a corpus's own claim is not a licence on file"
    assert prov["license_claimed"] == corpus.meta["license"]


def test_registered_provenance_names_the_licence_and_the_verdict():
    prov = provenance(load_corpus(resolve_corpus("cleveland")))
    assert prov["id"] == "cleveland"
    assert prov["license"] == "CC0-1.0"
    assert prov["robots_verdict"] == "allowed"
    assert prov["registered"] is True


def _unregistered_copy(tmp_name: str) -> Path:
    """A corpus identical to a shipped one but with a name no source claims."""
    source_path = resolve_corpus("cleveland")
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["corpus"]["name"] = "labeldesk-test-unregistered"
    target = source_path.with_name(tmp_name)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def test_pipeline_refuses_the_model_for_an_unregistered_corpus():
    """The point of the register: policy is asked before the network, not after."""
    target = _unregistered_copy("frozen_corpus_test_unregistered.json")
    try:
        corpus = load_corpus(target)
        result = draft(corpus, "1970.36", llm="replay")
    finally:
        target.unlink(missing_ok=True)

    assert result["status"] == "drafted", "offline drafting must be unaffected"
    assert result["label_source"] == "offline_template"
    block = result["llm"]
    assert block["requested"] is True
    assert block["applied"] is False
    assert block["reason"] == "source_policy"
    assert block["attempts"] == 0, "nothing was sent, so nothing was attempted"
    assert result["provenance"]["registered"] is False


def test_pipeline_still_reaches_the_model_for_a_registered_corpus():
    """The same record and the same flag, but a source that grants ai_input."""
    corpus = load_corpus(resolve_corpus("cleveland"))
    result = draft(corpus, "1970.36", llm="replay")
    assert result["llm"]["reason"] != "source_policy"


def test_offline_drafting_ignores_policy_entirely():
    corpus = load_corpus(resolve_corpus("cleveland"))
    result = draft(corpus, "1970.36")
    assert result["status"] == "drafted"
    assert result["llm"]["requested"] is False
    assert result["provenance"]["id"] == "cleveland"


def test_refusals_carry_provenance_too():
    corpus = load_corpus(resolve_corpus("cleveland"))
    result = draft(corpus, "not-a-number")
    assert result["status"] == "refused"
    assert result["provenance"]["id"] == "cleveland"


def test_register_path_is_inside_the_repository():
    assert REGISTER_PATH.exists()
    assert ROOT in REGISTER_PATH.parents


def test_format_table_lists_every_source():
    table = format_table()
    for source in sources():
        assert source["id"] in table
    assert "ai_input" not in table.splitlines()[0].lower()  # header stays terse
