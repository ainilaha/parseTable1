"""Deterministic helpers for identifying likely categorical levels."""

from __future__ import annotations

import re

from table1_parser.schemas import RowView


COMMON_LEVEL_LABELS = {
    "male",
    "female",
    "yes",
    "no",
    "never",
    "former",
    "current",
    "current smoker",
    "ex smoker",
    "non smoker",
    "high school",
    "more than high school",
    "less than high school",
    "hs",
}
VARIABLE_LIKE_PATTERN = re.compile(
    r"\b(age|bmi|education|status|race|sex|smoking|income|pressure|cholesterol)\b",
    re.IGNORECASE,
)


def is_common_level_label(label: str) -> bool:
    """Return whether normalized text strongly resembles a categorical level."""
    normalized = " ".join(label.lower().split())
    compact = normalized.replace(" ", "")
    return (
        normalized in COMMON_LEVEL_LABELS
        or compact in {"<hs", ">hs", "highschool", "morethanhighschool"}
        or normalized.startswith("<")
        or normalized.startswith(">")
    )


def is_likely_level_row(row_view: RowView) -> bool:
    """Detect whether a body row label looks like a categorical level."""
    label = row_view.first_cell_normalized
    word_count = len(label.split())
    return (
        bool(label)
        and row_view.has_trailing_values
        and not bool(VARIABLE_LIKE_PATTERN.search(label))
        and (
            is_common_level_label(label)
            or (
                word_count <= 3
                and len(label) <= 24
                and "," not in row_view.first_cell_raw
                and "/" not in row_view.first_cell_raw
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
        if classification == "unknown" and level_rows:
            break
        if classification != "level_row":
            break
    return level_rows
