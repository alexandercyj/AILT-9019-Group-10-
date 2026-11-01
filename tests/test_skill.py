"""The skill file must describe the program that actually runs.

A skill is a contract handed to another agent environment. If the contract drifts
from the code, the calling agent keeps its side and the guarantee is lost, so the
document is tested like any other artefact.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from labeldesk import load_corpus
from labeldesk.pipeline import REASON_TEXT, draft

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "labeldesk" / "SKILL.md"


@pytest.fixture(scope="module")
def text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_skill_file_exists_with_frontmatter(text):
    assert text.startswith("---\n")
    frontmatter = text.split("---", 2)[1]
    assert "name: labeldesk" in frontmatter
    assert "description:" in frontmatter


def test_skill_documents_the_real_invocation(text):
    assert "python3 -m labeldesk <catalogue number> --json" in text
    assert "--llm" in text and "--replay" in text and "--corpus" in text


def test_skill_lists_exactly_the_refusal_reasons_the_code_emits(text):
    for reason in REASON_TEXT:
        assert reason in text, f"{reason} is not documented"
    documented = set(re.findall(r"`(out_of_corpus|missing_required_field|out_of_scope)`", text))
    assert documented == set(REASON_TEXT)


def test_skill_documents_the_real_result_keys(text):
    corpus = load_corpus()
    result = draft(corpus, "14.40.377")
    for key in ("status", "label", "claims", "citations", "padding", "notice",
                "word_count", "label_source", "checks", "llm", "record", "provenance"):
        assert f'"{key}"' in text, f"{key} is missing from the documented shape"
        assert key in result, f"{key} is missing from the real result"


def test_skill_documents_the_notice_verbatim(text):
    corpus = load_corpus()
    result = draft(corpus, "14.40.377")
    assert result["notice"] in text


def test_skill_states_the_guardrails_it_asks_the_caller_to_keep(text):
    lowered = text.lower()
    for phrase in ("never post-process a refusal", "never fill a blank field",
                   "checks.passed", "quote `notice`"):
        assert phrase in lowered


def test_the_documented_json_example_parses(text):
    block = re.search(r"```json\n(.*?)\n```", text, re.S)
    assert block, "the skill must show a parseable result object"
    payload = json.loads(block.group(1))
    assert payload["status"] == "drafted"
    assert payload["checks"]["passed"] is True
