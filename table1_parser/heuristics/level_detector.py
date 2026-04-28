"""Deterministic helpers for identifying likely categorical levels."""

from __future__ import annotations

import re

from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.schemas import RowView
from table1_parser.text_cleaning import clean_text


SUMMARY_LABEL_PATTERN = re.compile(
    r"\b(mean|sd|median|iqr|range|min|max)\b",
    re.IGNORECASE,
)
COUNT_LIKE_VALUE_PATTERNS = {"count_pct", "n_only"}
PERCENT_FRAGMENT_PATTERN = re.compile(r"^\(\s*\d+(?:\.\d+)?%\s*\)$")


def is_common_level_label(label: str) -> bool:
    """Return whether normalized text has a structural level cue."""
    normalized = " ".join(label.lower().split())
    compact = normalized.replace(" ", "")
    return (
        compact in {"<hs", ">hs", "<=hs", ">=hs", "≤hs", "≥hs"}
        or normalized.startswith(("<", ">", "≤", "≥"))
    )


def is_likely_level_row(
    row_view: RowView,
    statistic_col_indices: set[int] | None = None,
) -> bool:
    """Detect whether a body row label looks like a categorical level."""
    label = row_view.first_cell_normalized
    word_count = len(label.split())
    trailing_cells = [
        clean_text(row_view.raw_cells[col_idx])
        for col_idx in range(1, len(row_view.raw_cells))
        if col_idx not in (statistic_col_indices or set()) and clean_text(row_view.raw_cells[col_idx])
    ]
    trailing_values_are_count_like = False
    count_like_value_count = 0
    trailing_idx = 0
    while trailing_idx < len(trailing_cells):
        pattern = detect_value_pattern(trailing_cells[trailing_idx]).pattern
        if pattern in COUNT_LIKE_VALUE_PATTERNS:
            trailing_values_are_count_like = True
            count_like_value_count += 1
            if (
                pattern == "n_only"
                and trailing_idx + 1 < len(trailing_cells)
                and PERCENT_FRAGMENT_PATTERN.fullmatch(trailing_cells[trailing_idx + 1])
            ):
                trailing_idx += 2
                continue
            trailing_idx += 1
            continue
        if pattern == "p_value" and count_like_value_count >= 1:
            trailing_idx += 1
            continue
        if trailing_idx == 0 and len(trailing_cells) >= 3:
            remaining_patterns = [
                detect_value_pattern(cell).pattern
                for cell in trailing_cells[1:]
            ]
            if sum(candidate in COUNT_LIKE_VALUE_PATTERNS for candidate in remaining_patterns) >= 2:
                trailing_idx += 1
                continue
        trailing_values_are_count_like = False
        break
    return (
        bool(label)
        and row_view.has_trailing_values
        and not bool(SUMMARY_LABEL_PATTERN.search(row_view.first_cell_raw))
        and trailing_values_are_count_like
        and (
            is_common_level_label(label)
            or (
                word_count <= 4
                and len(label) <= 32
                and "," not in row_view.first_cell_raw
                and row_view.numeric_cell_count > 0
            )
        )
    )


def detect_level_row_indices(
    parent_row_idx: int,
    row_order: list[int],
    classifications_by_row: dict[int, str],
) -> list[int]:
    """Collect contiguous level rows that belong to a candidate parent variable."""
    try:
        parent_position = row_order.index(parent_row_idx)
    except ValueError:
        return []

    level_rows: list[int] = []
    for row_idx in row_order[parent_position + 1 :]:
        classification = classifications_by_row.get(row_idx, "unknown")
        if classification == "level_row":
            level_rows.append(row_idx)
            continue
        if classification == "unknown":
            continue
        if classification != "level_row":
            break
    return level_rows
