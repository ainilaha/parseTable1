"""Shared parser-facing text cleaning helpers."""

from __future__ import annotations

import re


WHITESPACE_PATTERN = re.compile(r"\s+")
EXTRACTOR_GLYPH_REPAIRS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("replacement_char_le_threshold", re.compile(r"(?:(?<=^)|(?<=[\s(\|>]))�\s*(?=\d)"), "<="),
)
DIRECT_SYMBOL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("<=", re.compile(r"<=|≤|≦|&le;")),
    (">=", re.compile(r">=|≥|≧|&ge;")),
    ("<", re.compile(r"(?<![<>=])(?:<|＜|&lt;)(?![=])")),
    (">", re.compile(r"(?<![<>=])(?:>|＞|&gt;)(?![=])")),
)
CANONICAL_SYMBOLS = ("<", "<=", ">", ">=")
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
    for _, pattern, replacement in EXTRACTOR_GLYPH_REPAIRS:
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


def summarize_text_cleaning_provenance(rows: list[list[str]]) -> dict[str, object]:
    """Summarize directly observed and reconstructed comparator symbols for one table grid."""
    observed_symbol_counts = {symbol: 0 for symbol in CANONICAL_SYMBOLS}
    reconstructed_symbol_counts = {symbol: 0 for symbol in CANONICAL_SYMBOLS}
    extractor_glyph_repair_rule_counts = {rule_name: 0 for rule_name, _, _ in EXTRACTOR_GLYPH_REPAIRS}
    cells_with_extractor_glyph_repairs = 0

    for row in rows:
        for cell in row:
            remaining = cell
            repaired_this_cell = False
            for rule_name, pattern, replacement in EXTRACTOR_GLYPH_REPAIRS:
                match_count = len(pattern.findall(remaining))
                if not match_count:
                    continue
                extractor_glyph_repair_rule_counts[rule_name] += match_count
                reconstructed_symbol_counts[replacement] += match_count
                repaired_this_cell = True
                remaining = pattern.sub(" ", remaining)
            if repaired_this_cell:
                cells_with_extractor_glyph_repairs += 1
            for symbol, pattern in DIRECT_SYMBOL_PATTERNS:
                observed_symbol_counts[symbol] += len(pattern.findall(remaining))

    return {
        "observed_symbol_counts": observed_symbol_counts,
        "reconstructed_symbol_counts": reconstructed_symbol_counts,
        "total_observed_symbol_count": sum(observed_symbol_counts.values()),
        "total_reconstructed_symbol_count": sum(reconstructed_symbol_counts.values()),
        "extractor_glyph_repair_rule_counts": extractor_glyph_repair_rule_counts,
        "cells_with_extractor_glyph_repairs": cells_with_extractor_glyph_repairs,
    }
