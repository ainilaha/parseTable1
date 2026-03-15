"""Deterministic text cleaning helpers."""

from __future__ import annotations

import re


WHITESPACE_PATTERN = re.compile(r"\s+")
DASH_PATTERN = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]+")


def clean_text(value: str) -> str:
    """Collapse whitespace and normalize dash variants without dropping content."""
    normalized = DASH_PATTERN.sub("-", value)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()
