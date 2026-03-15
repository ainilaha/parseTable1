"""Deterministic row classification on top of NormalizedTable row views."""

from __future__ import annotations

import re
from collections.abc import Sequence

from table1_parser.heuristics.level_detector import is_common_level_label, is_likely_level_row
from table1_parser.heuristics.models import RowClassification
from table1_parser.schemas import NormalizedTable, RowView


CATEGORICAL_PARENT_CUE_PATTERN = re.compile(
    r"(?:n\s*\(%\)|no\.\s*\(%\)|\bpercent\b|\bcategory\b|\blevel\b)",
    re.IGNORECASE,
)
CONTINUOUS_TEXT_CUE_PATTERN = re.compile(
    r"(?:\bmean\b|\bsd\b|\bmedian\b|\biqr\b|mean\s*[±+-]\s*sd|mean\s*\(\s*sd\s*\))",
    re.IGNORECASE,
)
DECIMAL_SUMMARY_PATTERN = re.compile(
    r"^\s*[<>]?\d+\.\d+\s*(?:\(\s*[<>]?\d+(?:\.\d+)?(?:\s*[,/-]\s*[<>]?\d+(?:\.\d+)?)?\s*\))?\s*$"
)
INTEGER_VALUE_PATTERN = re.compile(r"^\s*\d+\s*$")


def _trailing_cells(row_view: RowView) -> list[str]:
    """Return populated trailing cells after the first label column."""
    return [cell for cell in row_view.raw_cells[1:] if cell]


def _trailing_numeric_count(row_view: RowView) -> int:
    """Count numeric-looking trailing cells without relying on full parsing."""
    return sum(any(char.isdigit() for char in cell) for cell in row_view.raw_cells[1:] if cell)


def _nonempty_trailing_count(row_view: RowView) -> int:
    """Count populated trailing cells after the first label column."""
    return len(_trailing_cells(row_view))


def _has_categorical_parent_cue(row_view: RowView) -> bool:
    """Return whether the row text explicitly signals a categorical parent."""
    return bool(CATEGORICAL_PARENT_CUE_PATTERN.search(row_view.first_cell_raw))


def _summary_like_trailing_count(trailing_cells: Sequence[str]) -> int:
    """Count trailing cells that look like summary statistics rather than category counts."""
    return sum("±" in cell or bool(DECIMAL_SUMMARY_PATTERN.match(cell)) for cell in trailing_cells)


def _integer_only_trailing_count(trailing_cells: Sequence[str]) -> int:
    """Count trailing cells that contain plain integer values."""
    return sum(bool(INTEGER_VALUE_PATTERN.match(cell)) for cell in trailing_cells)


def _has_continuous_cue(row_view: RowView) -> bool:
    """Return whether the row text or values resemble a continuous summary."""
    trailing_cells = _trailing_cells(row_view)
    if CONTINUOUS_TEXT_CUE_PATTERN.search(row_view.first_cell_raw):
        return True
    if CONTINUOUS_TEXT_CUE_PATTERN.search(" ".join(trailing_cells)):
        return True
    summary_like_cells = _summary_like_trailing_count(trailing_cells)
    return bool(trailing_cells) and summary_like_cells >= max(1, len(trailing_cells) // 2 + 1)


def _has_strong_continuous_cue(row_view: RowView) -> bool:
    """Return whether the row explicitly names a summary-statistic format."""
    return bool(CONTINUOUS_TEXT_CUE_PATTERN.search(row_view.first_cell_raw))


def _has_strong_continuous_layout(row_view: RowView) -> bool:
    """Return whether the row strongly resembles a one-line continuous summary."""
    return _has_strong_continuous_cue(row_view) or _summary_like_trailing_count(_trailing_cells(row_view)) >= 2


def _trailing_is_sparse(row_view: RowView) -> bool:
    """Return whether the row leaves most trailing cells empty."""
    return _nonempty_trailing_count(row_view) <= 1


def _is_more_indented(row_view: RowView, reference_row: RowView | None) -> bool:
    """Return whether a row is more indented than a nearby reference row."""
    return (
        reference_row is not None
        and row_view.indent_level is not None
        and reference_row.indent_level is not None
        and row_view.indent_level > reference_row.indent_level
    )


def _is_strong_variable_boundary(row_view: RowView) -> bool:
    """Return whether a row strongly suggests the start of a different variable block."""
    return (
        not row_view.has_trailing_values
        or _has_categorical_parent_cue(row_view)
        or _has_strong_continuous_cue(row_view)
    )


def _count_plausible_child_levels(following_row_views: Sequence[RowView]) -> int:
    """Count plausible child levels until the next strong variable boundary."""
    child_level_count = 0
    for next_row in following_row_views:
        if is_likely_level_row(next_row):
            child_level_count += 1
            continue
        if child_level_count > 0 or _is_strong_variable_boundary(next_row):
            break
    return child_level_count


def _count_more_indented_child_levels(
    parent_row_view: RowView,
    following_row_views: Sequence[RowView],
) -> int:
    """Count plausible child levels that are also more indented than the parent."""
    child_level_count = 0
    for next_row in following_row_views:
        if is_likely_level_row(next_row):
            if _is_more_indented(next_row, parent_row_view):
                child_level_count += 1
            continue
        if child_level_count > 0 or _is_strong_variable_boundary(next_row):
            break
    return child_level_count


def _looks_continuous(
    row_view: RowView,
    child_level_count: int = 0,
    has_categorical_parent_cue: bool = False,
) -> bool:
    """Return whether a row resembles a one-line continuous-variable summary."""
    label = row_view.first_cell_normalized
    trailing_cells = _trailing_cells(row_view)
    trailing_numeric = _trailing_numeric_count(row_view)
    strong_continuous_layout = _has_strong_continuous_layout(row_view)
    return (
        row_view.has_trailing_values
        and bool(trailing_cells)
        and (strong_continuous_layout or child_level_count < 2)
        and not has_categorical_parent_cue
        and _has_continuous_cue(row_view)
        and (
            trailing_numeric >= max(2, len(trailing_cells) // 2 + 1)
            or (len(trailing_cells) == 1 and "(" in trailing_cells[0])
        )
        and not is_common_level_label(label)
    )


def _looks_scalar_count_row(
    row_view: RowView,
    child_level_count: int = 0,
    has_categorical_parent_cue: bool = False,
) -> bool:
    """Return whether a short label with integer counts should behave as a one-row variable."""
    label = row_view.first_cell_normalized
    trailing_cells = _trailing_cells(row_view)
    integer_only_count = _integer_only_trailing_count(trailing_cells)
    word_count = len(label.split())
    return (
        row_view.has_trailing_values
        and bool(trailing_cells)
        and child_level_count == 0
        and not has_categorical_parent_cue
        and not _has_strong_continuous_layout(row_view)
        and not is_common_level_label(label)
        and word_count <= 2
        and len(label) <= 16
        and integer_only_count == len(trailing_cells)
    )


def _looks_like_level_continuation(
    row_view: RowView,
    child_level_count: int,
    strong_continuous_layout: bool,
    categorical_parent_cue: bool,
) -> bool:
    """Return whether a row should continue an existing categorical run."""
    trailing_numeric = _trailing_numeric_count(row_view)
    sparse_trailing = _trailing_is_sparse(row_view)
    return (
        row_view.has_trailing_values
        and not categorical_parent_cue
        and not strong_continuous_layout
        and not _looks_scalar_count_row(
            row_view,
            child_level_count=child_level_count,
            has_categorical_parent_cue=categorical_parent_cue,
        )
        and not (sparse_trailing and child_level_count >= 2 and trailing_numeric > 0)
    )


def classify_row(
    row_view: RowView,
    previous_classification: str | None = None,
    previous_row_view: RowView | None = None,
    next_row_view: RowView | None = None,
    following_row_views: Sequence[RowView] | None = None,
) -> RowClassification:
    """Classify a normalized body row conservatively."""
    label = row_view.first_cell_normalized
    word_count = len(label.split())
    trailing_cells = _trailing_cells(row_view)
    trailing_numeric = _trailing_numeric_count(row_view)
    next_is_level_like = bool(next_row_view and is_likely_level_row(next_row_view))
    categorical_parent_cue = _has_categorical_parent_cue(row_view)
    child_level_count = _count_plausible_child_levels(following_row_views or [])
    indented_child_level_count = _count_more_indented_child_levels(row_view, following_row_views or [])
    strong_continuous_layout = _has_strong_continuous_layout(row_view)
    sparse_trailing = _trailing_is_sparse(row_view)
    more_indented_than_previous = _is_more_indented(row_view, previous_row_view)

    if (
        previous_classification in {"variable_header", "level_row"}
        and _looks_like_level_continuation(
            row_view,
            child_level_count=child_level_count,
            strong_continuous_layout=strong_continuous_layout,
            categorical_parent_cue=categorical_parent_cue,
        )
    ):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="level_row",
            confidence=0.94 if more_indented_than_previous else (0.92 if is_common_level_label(label) else 0.78),
        )

    if strong_continuous_layout and row_view.has_trailing_values:
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="continuous_variable_row",
            confidence=0.92,
        )

    if is_common_level_label(label) and row_view.has_trailing_values:
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="level_row",
            confidence=0.9,
        )

    if categorical_parent_cue or (
        sparse_trailing
        and child_level_count >= 1
        and (not row_view.has_trailing_values or trailing_numeric > 0)
    ) or (
        not strong_continuous_layout and child_level_count >= 2
        and (not row_view.has_trailing_values or trailing_numeric > 0)
    ) or (
        sparse_trailing
        and indented_child_level_count >= 2
    ):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="variable_header",
            confidence=0.9 if categorical_parent_cue and child_level_count >= 2 else (0.88 if indented_child_level_count >= 2 else 0.84),
        )

    if _looks_continuous(
        row_view,
        child_level_count=child_level_count,
        has_categorical_parent_cue=categorical_parent_cue,
    ):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="continuous_variable_row",
            confidence=0.88,
        )

    if _looks_scalar_count_row(
        row_view,
        child_level_count=child_level_count,
        has_categorical_parent_cue=categorical_parent_cue,
    ):
        return RowClassification(
            row_idx=row_view.row_idx,
            classification="continuous_variable_row",
            confidence=0.8,
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

    if row_view.has_trailing_values and trailing_numeric > 0 and trailing_numeric <= 2 and next_is_level_like:
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
        previous_row = table.row_views[index - 1] if index > 0 else None
        next_row = table.row_views[index + 1] if index + 1 < len(table.row_views) else None
        classifications.append(
            classify_row(
                row_view,
                previous_classification=previous,
                previous_row_view=previous_row,
                next_row_view=next_row,
                following_row_views=table.row_views[index + 1 :],
            )
        )
    return classifications
