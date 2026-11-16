"""The shipped reader must not depend on whoever built it having an API key.

`labeldesk.html` embeds pipeline output. If that output records
`llm.has_key` from the process environment, a clean checkout fails the
byte-for-byte rebuild and a configured key can land in a committed file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_standalone as builder  # noqa: E402

from labeldesk import draft, load_corpus  # noqa: E402

SENTINEL = "sk-test-sentinel-not-a-credential"


def test_offline_and_replay_do_not_record_an_ambient_key(monkeypatch):
    monkeypatch.setenv("LABELDESK_API_KEY", SENTINEL)
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL)
    monkeypatch.setenv("BAILIAN_API_KEY", SENTINEL)
    monkeypatch.setenv("LABELDESK_BASE_URL", "https://secret.example.invalid/v1")
    monkeypatch.setenv("LABELDESK_MODEL", "secret-model")
    corpus = load_corpus()
    offline = draft(corpus, "14.40.377")
    replay = draft(corpus, "14.40.377", llm="replay")
    assert offline["llm"]["has_key"] is False
    assert replay["llm"]["has_key"] is False
    assert offline["llm"]["base_url"].startswith("https://token-plan.")
    blob = json.dumps({"offline": offline, "replay": replay})
    assert SENTINEL not in blob
    assert "secret.example.invalid" not in blob
    assert "secret-model" not in blob


def test_standalone_build_is_stable_when_a_key_is_configured(monkeypatch):
    before = builder.build()
    monkeypatch.setenv("LABELDESK_API_KEY", SENTINEL)
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL)
    monkeypatch.setenv("BAILIAN_API_KEY", SENTINEL)
    monkeypatch.setenv("LABELDESK_BASE_URL", "https://secret.example.invalid/v1")
    monkeypatch.setenv("LABELDESK_MODEL", "secret-model")
    after = builder.build()
    assert after == before
    assert SENTINEL not in after
    assert "secret.example.invalid" not in after
    assert "secret-model" not in after


@pytest.mark.parametrize("mode", ["off", "replay"])
def test_public_result_has_no_key_fingerprint(monkeypatch, mode):
    monkeypatch.setenv("LABELDESK_API_KEY", SENTINEL)
    corpus = load_corpus()
    kwargs = {"llm": "replay"} if mode == "replay" else {}
    result = draft(corpus, "14.40.377", **kwargs)
    assert SENTINEL[-4:] not in json.dumps(result["llm"])
