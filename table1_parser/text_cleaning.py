"""Shared parser-facing text cleaning helpers."""

from __future__ import annotations

import re


WHITESPACE_PATTERN = re.compile(r"\s+")
EXTRACTOR_GLYPH_REPAIRS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:(?<=^)|(?<=[\s(\|>]))�\s*(?=\d)"), "<="),
)
HTML_ENTITY_MAP = {
    "&lt;": "<",
    "&gt;": ">",
    "&le;": "<=",
    "&ge;": ">=",
}
SYMBOL_TRANSLATIONS = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\u2264": "<=",
        "\u2265": ">=",
        "\u2266": "<=",
        "\u2267": ">=",
        "\uff1c": "<",
        "\uff1e": ">",
    }
)


def repair_extractor_glyph_failures(value: str) -> str:
    """Repair a narrow set of known extractor glyph-to-symbol failures conservatively."""
    repaired = value
    for pattern, replacement in EXTRACTOR_GLYPH_REPAIRS:
        repaired = pattern.sub(replacement, repaired)
    return repaired


def clean_text(value: str) -> str:
    """Normalize parser-facing text while preserving the original extraction elsewhere."""
    normalized = repair_extractor_glyph_failures(value)
    for source, target in HTML_ENTITY_MAP.items():
        normalized = normalized.replace(source, target)
    normalized = normalized.translate(SYMBOL_TRANSLATIONS)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()
