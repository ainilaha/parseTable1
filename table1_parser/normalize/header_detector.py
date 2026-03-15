"""Heuristics for distinguishing header rows from body rows."""

from __future__ import annotations

import re


NUMERIC_PATTERN = re.compile(r"\d")
HEADER_KEYWORD_PATTERN = re.compile(r"\b(overall|p-?value|total|n|%)\b", re.IGNORECASE)


def _numeric_density(row: list[str]) -> float:
    """Compute the fraction of populated cells containing numeric content."""
    populated = [cell for cell in row if cell]
    if not populated:
        return 0.0
    numeric = [cell for cell in populated if NUMERIC_PATTERN.search(cell)]
    return len(numeric) / len(populated)


def _text_density(row: list[str]) -> float:
    """Compute the fraction of populated cells containing alphabetic content."""
    populated = [cell for cell in row if cell]
    if not populated:
        return 0.0
    text_like = [cell for cell in populated if any(char.isalpha() for char in cell)]
    return len(text_like) / len(populated)


def header_score(row: list[str], row_idx: int) -> float:
    """Score a row for header-likeness using simple deterministic signals."""
    joined = " ".join(cell for cell in row if cell)
    score = 0.0
    if row_idx < 2:
        score += 0.25
    if HEADER_KEYWORD_PATTERN.search(joined):
        score += 0.4
    if _text_density(row) >= 0.75:
        score += 0.2
    if _numeric_density(row) <= 0.25:
        score += 0.2
    return min(score, 1.0)


def detect_header_rows(rows: list[list[str]]) -> tuple[list[int], list[int]]:
    """Identify likely header rows near the top of the table."""
    header_rows: list[int] = []
    scan_limit = min(len(rows), 3)

    for row_idx in range(scan_limit):
        score = header_score(rows[row_idx], row_idx)
        if score >= 0.55:
            header_rows.append(row_idx)
        elif row_idx == 0 and HEADER_KEYWORD_PATTERN.search(" ".join(rows[row_idx])):
            header_rows.append(row_idx)
        elif header_rows:
            break

    body_rows = [row_idx for row_idx in range(len(rows)) if row_idx not in header_rows]
    return header_rows, body_rows
