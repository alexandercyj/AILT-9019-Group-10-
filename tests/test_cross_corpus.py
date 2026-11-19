"""Cross-corpus refusals follow blank required fields, not a copied reason sentence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("title", "object_date", "medium", "place_or_culture", "credit_line")
KEYS = ("OPENAI_API_KEY", "LABELDESK_API_KEY", "BAILIAN_API_KEY", "DASHSCOPE_API_KEY", "ALIYUN_API_KEY")


def _env() -> dict:
    env = os.environ.copy()
    for key in KEYS:
        env.pop(key, None)
    return env


def test_blank_fields_are_the_only_refusals(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "cross_corpus.py"), "--reports", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=_env(),
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads((tmp_path / "cross_corpus.json").read_text(encoding="utf-8"))
    by_alias = {row["alias"]: row for row in report["runs"]}
    assert set(by_alias) == {"cleveland", "egyptian", "primary"}

    drafted = refused = 0
    accepted = discarded = 0
    for alias, filename in (
        ("primary", "frozen_corpus.json"),
        ("egyptian", "frozen_corpus_egyptian.json"),
        ("cleveland", "frozen_corpus_cleveland.json"),
    ):
        corpus = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
        offline = {item["catalogue_number"]: item for item in by_alias[alias]["offline"]["outcomes"]}
        replay = {item["catalogue_number"]: item for item in by_alias[alias]["llm"]["outcomes"]}
        assert by_alias[alias]["offline"]["check_failures"] == []
        assert by_alias[alias]["offline"]["expectation_failures"] == []
        assert by_alias[alias]["llm"]["check_failures"] == []
        for record in corpus["records"]:
            blank = [field for field in REQUIRED if not str(record.get(field) or "").strip()]
            item = offline[record["catalogue_number"]]
            if blank:
                assert item["status"] == "refused"
                assert item["reason"] == "missing_required_field"
                assert item["missing_fields"] == blank
                refused += 1
            else:
                assert item["status"] == "drafted"
                assert item["checks_passed"] is True
                drafted += 1
            again = replay[record["catalogue_number"]]
            assert again["status"] == item["status"]
            if again["llm_applied"] is True:
                accepted += 1
            elif again["llm_applied"] is False:
                assert again["llm_reason"] == "drops_field_content"
                discarded += 1

    assert drafted == 37
    assert refused == 3
    assert accepted == 35
    assert discarded == 2
    assert (ROOT / "eval" / "reports" / "cross_corpus.md").read_text(encoding="utf-8").count("live model call") >= 1
