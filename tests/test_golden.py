"""The evaluation itself is part of the test suite.

If the golden set regresses, this file fails before anyone records a demo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_golden_set_passes_every_gate():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "evaluate.py"), "--quiet"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "17/17 cases passed" in completed.stdout


def test_report_files_are_written():
    subprocess.run(
        [sys.executable, str(ROOT / "eval" / "evaluate.py"), "--quiet"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    assert (ROOT / "eval" / "reports" / "golden_report.md").exists()
    assert (ROOT / "eval" / "reports" / "golden_report.json").exists()


def test_cli_drafts_a_label():
    completed = subprocess.run(
        [sys.executable, "-m", "labeldesk", "14.40.377"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 0
    assert "STATUS  DRAFTED" in completed.stdout
    assert "1713–22" in completed.stdout


def test_cli_refusal_exit_code():
    completed = subprocess.run(
        [sys.executable, "-m", "labeldesk", "62.98.1"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 3
    assert "REFUSED" in completed.stdout
