"""Deterministic row classification on top of NormalizedTable row views."""

from __future__ import annotations

import re

from table1_parser.heuristics.level_detector import is_common_level_label, is_likely_level_row
from table1_parser.heuristics.models import RowClassification
from table1_parser.schemas import NormalizedTable, RowView


VARIABLE_HINT_PATTERN = re.compile(
    r"\b(age|bmi|status|education|race|sex|smoking|income|blood pressure|cholesterol)\b",
    re.IGNORECASE,
)


def _trailing_cells(row_view: RowView) -> list[str]:
    """Return populated trailing cells after the first label column."""
    return [cell for cell in row_view.raw_cells[1:] if cell]


def _trailing_numeric_count(row_view: RowView) -> int:
    """Count numeric-looking trailing cells without relying on full parsing."""
    return sum(any(char.isdigit() for char in cell) for cell in row_view.raw_cells[1:] if cell)


def _looks_continuous(row_view: RowView) -> bool:
    """Return whether a row resembles a one-line continuous-variable summary."""
    label = row_view.first_cell_normalized
    trailing_cells = _trailing_cells(row_view)
    trailing_numeric = _trailing_numeric_count(row_view)
    strong_continuous_signal = (
        "," in row_view.first_cell_raw
        or "/" in row_view.first_cell_raw
        or "±" in " ".join(trailing_cells)
        or bool(VARIABLE_HINT_PATTERN.search(label))
    )
    return (
        row_view.has_trailing_values
        and bool(trailing_cells)
        and (
            trailing_numeric >= max(2, len(trailing_cells) // 2 + 1)
            or (len(trailing_cells) == 1 and strong_continuous_signal and "(" in trailing_cells[0])
        )
        and not is_common_level_label(label)
        and strong_continuous_signal
    )


def classify_row(
    row_view: RowView,
    previous_classification: str | None = None,
    next_row_view: RowView | None = None,
) -> RowClassification:
    """Classify a normalized body row conservatively."""
    label = row_view.first_cell_normalized
    word_count = len(label.split())
    trailing_cells = _trailing_cells(row_view)
    trailing_numeric = _trailing_numeric_count(row_view)
    next_is_level_like = bool(next_row_view and is_likely_level_row(next_row_view))

    if _looks_continuous(row_view):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="continuous_variable_row",
            confidence=0.88,
        )

    if is_likely_level_row(row_view):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="level_row",
            confidence=0.9 if is_common_level_label(label) else 0.76,
        )

    if not row_view.has_trailing_values:
        if next_is_level_like:
            return RowClassification(
                row_idx=row_view.row_idx,
                classification="variable_header",
                confidence=0.86,
            )
        if word_count <= 5 and not is_common_level_label(label):
            return RowClassification(
                row_idx=row_view.row_idx,
                classification="section_header",
                confidence=0.72,
            )

    if row_view.has_trailing_values and trailing_numeric <= 2 and next_is_level_like:
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="variable_header",
            confidence=0.78,
        )

    if (
        previous_classification == "variable_header"
        and row_view.has_trailing_values
        and trailing_numeric > 0
        and word_count <= 4
    ):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="level_row",
            confidence=0.7,
        )

    return RowClassification(row_idx=row_view.row_idx, classification="unknown", confidence=0.45)


def classify_rows(table: NormalizedTable) -> list[RowClassification]:
    """Classify all normalized body rows in order."""
    classifications: list[RowClassification] = []
    for index, row_view in enumerate(table.row_views):
        previous = classifications[-1].classification if classifications else None
        next_row = table.row_views[index + 1] if index + 1 < len(table.row_views) else None
        classifications.append(classify_row(row_view, previous_classification=previous, next_row_view=next_row))
    return classifications
