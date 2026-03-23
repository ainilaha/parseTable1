"""Deterministic value-pattern detection for raw cell strings."""

from __future__ import annotations

import re

from table1_parser.heuristics.models import ValuePatternGuess
from table1_parser.normalize.cleaner import clean_text


INTEGER_TOKEN = r"(?:\d{1,3}(?:,\d{3})*|\d+)"
DECIMAL_TOKEN = r"\d+(?:\.\d+)?"
COUNT_PCT_PATTERN = re.compile(rf"^{INTEGER_TOKEN}\s*\(\s*{DECIMAL_TOKEN}%?\s*\)$")
MEAN_SD_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?\s*(?:\(\s*-?\d+(?:\.\d+)?\s*\)|±\s*-?\d+(?:\.\d+)?)$")
MEDIAN_IQR_PATTERN = re.compile(
    r"^-?\d+(?:\.\d+)?\s*\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\)$"
)
P_VALUE_PATTERN = re.compile(r"^(?:[<>]=?\s*)?(?:0?\.\d+|\.\d+|1\.0+)$", re.IGNORECASE)
N_ONLY_PATTERN = re.compile(rf"^{INTEGER_TOKEN}$")


def _normalize_p_value_candidate(value: str) -> str:
    """Drop a literal p-prefix while preserving comparator symbols."""
    normalized = clean_text(value).lower().strip()
    if not normalized.startswith("p"):
        return normalized
    remainder = normalized[1:].lstrip()
    if remainder.startswith(("=", ":")):
        return remainder[1:].lstrip()
    return remainder


def detect_value_pattern(raw_value: str) -> ValuePatternGuess:
    """Classify a raw value string into a conservative pattern family."""
    value = clean_text(raw_value)
    lowered = _normalize_p_value_candidate(raw_value)

    if MEDIAN_IQR_PATTERN.fullmatch(lowered):
        return ValuePatternGuess(raw_value=raw_value, pattern="median_iqr", confidence=0.95)
    if COUNT_PCT_PATTERN.fullmatch(lowered):
        return ValuePatternGuess(raw_value=raw_value, pattern="count_pct", confidence=0.95)
    if value.startswith("<") or value.startswith(">"):
        if P_VALUE_PATTERN.fullmatch(lowered):
            return ValuePatternGuess(raw_value=raw_value, pattern="p_value", confidence=0.98)
    if P_VALUE_PATTERN.fullmatch(lowered):
        return ValuePatternGuess(raw_value=raw_value, pattern="p_value", confidence=0.85)
    if MEAN_SD_PATTERN.fullmatch(value):
        return ValuePatternGuess(raw_value=raw_value, pattern="mean_sd", confidence=0.9)
    if N_ONLY_PATTERN.fullmatch(value):
        return ValuePatternGuess(raw_value=raw_value, pattern="n_only", confidence=0.9)
    return ValuePatternGuess(raw_value=raw_value, pattern="unknown", confidence=0.4)
