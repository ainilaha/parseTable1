"""Heuristics for distinguishing header rows from body rows."""

from __future__ import annotations

import re


NUMERIC_PATTERN = re.compile(r"\d")
HEADER_KEYWORD_PATTERN = re.compile(r"\b(overall|p-?value|total|n|%)\b", re.IGNORECASE)
COUNT_ROW_LABEL_PATTERN = re.compile(r"^(n|N|no\.?|number)$")
TOP_RULE_GAP = 12.0
BOUNDARY_RULE_TOLERANCE = 3.0
MAX_HEADER_ROWS = 3


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
    first_cell = next((cell for cell in row if cell), "")
    score = 0.0
    if row_idx < 2:
        score += 0.25
    if HEADER_KEYWORD_PATTERN.search(joined):
        score += 0.4
    if _text_density(row) >= 0.75:
        score += 0.2
    if _numeric_density(row) <= 0.25:
        score += 0.2
    if row_idx > 0 and COUNT_ROW_LABEL_PATTERN.fullmatch(first_cell.strip()) and _numeric_density(row) >= 0.75:
        score -= 0.45
    return min(score, 1.0)


def _find_top_rule(sorted_rules: list[float], first_top: float) -> float | None:
    """Return the closest plausible top rule above the first row."""
    candidates = [rule_y for rule_y in sorted_rules if 0.0 <= first_top - rule_y <= TOP_RULE_GAP]
    if not candidates:
        return None
    return max(candidates)


def _find_boundary_rule(
    sorted_rules: list[float],
    current_bottom: float,
    next_top: float,
) -> float | None:
    """Return a separator rule near the gap between adjacent rows."""
    candidates = [
        rule_y
        for rule_y in sorted_rules
        if current_bottom - BOUNDARY_RULE_TOLERANCE <= rule_y <= next_top + BOUNDARY_RULE_TOLERANCE
    ]
    if not candidates:
        return None
    gap_midpoint = (current_bottom + next_top) / 2.0
    return min(candidates, key=lambda rule_y: abs(rule_y - gap_midpoint))


def _detect_header_rows_from_rules(
    rows: list[list[str]],
    row_bounds: list[tuple[float, float]] | None,
    horizontal_rules: list[float] | None,
) -> tuple[list[int], str | None]:
    """Use wide horizontal rules as strong optional signals for a top header block."""
    if not rows or not row_bounds or not horizontal_rules or len(row_bounds) != len(rows):
        return [], None

    sorted_rules = sorted(horizontal_rules)
    first_top = row_bounds[0][0]
    top_rule = _find_top_rule(sorted_rules, first_top)
    if top_rule is None:
        return [], None

    max_header_idx = min(len(rows) - 2, MAX_HEADER_ROWS - 1)
    for row_idx in range(max_header_idx + 1):
        current_bottom = row_bounds[row_idx][1]
        next_top = row_bounds[row_idx + 1][0]
        boundary_rule = _find_boundary_rule(sorted_rules, current_bottom, next_top)
        if boundary_rule is None:
            continue
        header_count = row_idx + 1
        if header_count <= 2:
            return list(range(header_count)), "strong"
        candidate_rows = rows[:header_count]
        average_score = sum(header_score(row, index) for index, row in enumerate(candidate_rows)) / len(candidate_rows)
        if average_score >= 0.5:
            return list(range(header_count)), "moderate"
    return [], None


def _detect_header_rows_by_content(rows: list[list[str]]) -> list[int]:
    """Identify likely header rows near the top of the table using text signals only."""
    header_rows: list[int] = []
    scan_limit = min(len(rows), MAX_HEADER_ROWS)

    for row_idx in range(scan_limit):
        score = header_score(rows[row_idx], row_idx)
        if score >= 0.55:
            header_rows.append(row_idx)
        elif row_idx == 0 and HEADER_KEYWORD_PATTERN.search(" ".join(rows[row_idx])):
            header_rows.append(row_idx)
        elif header_rows:
            break
    return header_rows


def detect_header_rows_with_metadata(
    rows: list[list[str]],
    *,
    row_bounds: list[tuple[float, float]] | None = None,
    horizontal_rules: list[float] | None = None,
) -> tuple[list[int], list[int], dict[str, object]]:
    """Identify likely header rows and expose how the decision was made."""
    content_headers = _detect_header_rows_by_content(rows)
    rule_based_headers, rule_strength = _detect_header_rows_from_rules(rows, row_bounds, horizontal_rules)

    if rule_strength == "strong":
        header_rows = rule_based_headers
        source = "horizontal_rules"
    elif rule_strength == "moderate" and len(rule_based_headers) <= len(content_headers):
        header_rows = rule_based_headers
        source = "horizontal_rules"
    else:
        header_rows = content_headers
        source = "content"

    body_rows = [row_idx for row_idx in range(len(rows)) if row_idx not in header_rows]
    metadata = {
        "source": source,
        "rule_strength": rule_strength,
        "rule_based_headers": rule_based_headers,
        "content_based_headers": content_headers,
        "rule_content_disagreement": bool(rule_based_headers and rule_based_headers != content_headers),
    }
    return header_rows, body_rows, metadata


def detect_header_rows(
    rows: list[list[str]],
    *,
    row_bounds: list[tuple[float, float]] | None = None,
    horizontal_rules: list[float] | None = None,
) -> tuple[list[int], list[int]]:
    """Identify likely header rows near the top of the table."""
    header_rows, body_rows, _ = detect_header_rows_with_metadata(
        rows,
        row_bounds=row_bounds,
        horizontal_rules=horizontal_rules,
    )
    return header_rows, body_rows
