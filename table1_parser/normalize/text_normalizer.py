"""Text normalization helpers for first-column labels."""

from __future__ import annotations

import re

from table1_parser.text_cleaning import clean_text


NON_ALNUM_PATTERN = re.compile(r"[^A-Za-z0-9]+")
NON_ALPHA_PATTERN = re.compile(r"[^A-Za-z]+")
ALPHA_BOUNDARY_SEPARATOR_PATTERN = re.compile(r"(?<=[A-Za-z])[^A-Za-z0-9\s]+(?=[A-Za-z])")


def _replace_pattern_with_space(value: str, pattern: re.Pattern[str]) -> str:
    """Replace separator-like spans with spaces without concatenating surviving tokens."""
    return clean_text(pattern.sub(" ", value))


def _preserve_alpha_boundaries(value: str) -> str:
    """Insert spaces where punctuation separates alphabetic tokens."""
    return ALPHA_BOUNDARY_SEPARATOR_PATTERN.sub(" ", value)


def normalize_label_text(value: str) -> str:
    """Normalize a label while preserving alphanumeric content."""
    cleaned = _preserve_alpha_boundaries(clean_text(value))
    return _replace_pattern_with_space(cleaned, NON_ALNUM_PATTERN)


def alpha_only_text(value: str) -> str:
    """Reduce text to alphabetic content only for comparison features."""
    cleaned = _preserve_alpha_boundaries(clean_text(value))
    return _replace_pattern_with_space(cleaned, NON_ALPHA_PATTERN)
