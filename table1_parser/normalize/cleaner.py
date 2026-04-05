"""Deterministic text cleaning helpers."""

from __future__ import annotations

import re


WHITESPACE_PATTERN = re.compile(r"\s+")
REPLACEMENT_CHAR_LE_THRESHOLD_PATTERN = re.compile(r"(?:(?<=^)|(?<=\s)|(?<=\())�\s*(?=\d)")
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


def canonicalize_symbols(value: str) -> str:
    """Normalize parser-facing symbol variants while keeping the input otherwise intact."""
    normalized = value
    for source, target in HTML_ENTITY_MAP.items():
        normalized = normalized.replace(source, target)
    # Some PDFs surface a broken <= glyph as the replacement character directly
    # before a numeric threshold such as "�0.12". Repair only this narrow case.
    normalized = REPLACEMENT_CHAR_LE_THRESHOLD_PATTERN.sub("<=", normalized)
    return normalized.translate(SYMBOL_TRANSLATIONS)


def clean_text(value: str) -> str:
    """Collapse whitespace and normalize symbol variants without dropping content."""
    normalized = canonicalize_symbols(value)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()
