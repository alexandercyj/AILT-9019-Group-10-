"""WCAG 2.x contrast for the colours the reader actually paints.

Normal text needs 4.5:1. The pairs below are the text and background
combinations in styles.css. A failing pair is a regression, not a sample.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")


def _channel(value: float) -> float:
    value = value / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    hex_colour = hex_colour.lstrip("#")
    red = int(hex_colour[0:2], 16)
    green = int(hex_colour[2:4], 16)
    blue = int(hex_colour[4:6], 16)
    return (
        0.2126 * _channel(red)
        + 0.7152 * _channel(green)
        + 0.0722 * _channel(blue)
    )


def contrast(foreground: str, background: str) -> float:
    lighter = max(luminance(foreground), luminance(background))
    darker = min(luminance(foreground), luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def variables() -> dict[str, str]:
    found = dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8})", CSS))
    return {name: value.lower() for name, value in found.items()}


PAIRS = (
    ("--ink", "--paper"),
    ("--muted", "--paper"),
    ("--muted", "--white"),
    ("--rust", "--paper"),
    ("--rust", "--white"),
    ("--green", "--paper"),
    ("--green", "--green-soft"),
    ("#ffffff", "--green"),
    ("#773c29", "--rust-soft"),
    ("#6f5728", "#f4edda"),
    ("#626864", "#e8e7df"),
    ("#626864", "#e7e5dd"),
)


def resolve(token: str, names: dict[str, str]) -> str:
    if token.startswith("--"):
        return names[token]
    return token


def test_declared_pairs_meet_aa_for_normal_text():
    names = variables()
    failures = []
    for foreground, background in PAIRS:
        ratio = contrast(resolve(foreground, names), resolve(background, names))
        if ratio < 4.5:
            failures.append(f"{foreground} on {background} = {ratio:.2f}")
    assert failures == []


def test_placeholder_greys_are_the_measured_tone():
    assert "#8b8d85" not in CSS
    assert "#868a81" not in CSS
    assert "#b1b3a9" not in CSS
    assert "#626864" in CSS
