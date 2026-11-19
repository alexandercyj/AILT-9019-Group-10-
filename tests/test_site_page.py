"""The local landing page is real, accessible, and does not pretend to be hosted."""

from __future__ import annotations

import re
from pathlib import Path

import test_contrast

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
LINKS = (ROOT / "links.txt").read_text(encoding="utf-8")


def _tokens() -> dict[str, str]:
    found = dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8})", PAGE))
    found["#ffffff"] = "#ffffff"
    return {name: value.lower() for name, value in found.items()}


def _colour(token: str, names: dict[str, str]) -> str:
    if token.startswith("--") or token in names:
        return names[token]
    return token


PAIRS = (
    ("--ink", "--paper"),
    ("--muted", "--paper"),
    ("--green", "--paper"),
    ("--green", "--green-soft"),
    ("--ink", "--white"),
    ("#ffffff", "--green"),
)


def test_landing_page_has_skip_link_and_main():
    assert 'lang="en"' in PAGE
    assert 'href="#main"' in PAGE
    assert 'class="skip-link"' in PAGE
    assert 'Skip to the main content' in PAGE
    assert '<main id="main">' in PAGE


def test_landing_page_colour_pairs_meet_aa():
    names = _tokens()
    failures = []
    for foreground, background in PAIRS:
        ratio = test_contrast.contrast(_colour(foreground, names), _colour(background, names))
        if ratio < 4.5:
            failures.append(f"{foreground} on {background} = {ratio:.2f}")
    assert failures == []


def test_landing_page_does_not_claim_a_host_or_videos():
    assert "It is not a published URL." in PAGE
    assert "GitHub Pages is not enabled" in PAGE
    assert "Do not treat a github.io address as this page." in PAGE
    assert "youtube.com/watch" not in PAGE.lower()
    assert "youtu.be/" not in PAGE.lower()
    assert "Public webpage: NOT YET PUBLISHED" in LINKS
    assert "Presentation YouTube: NOT YET RECORDED" in LINKS
    assert "Demo YouTube: NOT YET RECORDED" in LINKS


def test_landing_page_labeldesk_link_resolves():
    assert 'href="../labeldesk.html"' in PAGE
    assert (ROOT / "labeldesk.html").is_file()
    assert 'href="../links.txt"' in PAGE
    assert (ROOT / "links.txt").is_file()
