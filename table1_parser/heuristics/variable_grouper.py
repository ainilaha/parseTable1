"""Group normalized rows into deterministic candidate variable blocks."""

from __future__ import annotations

from table1_parser.heuristics.level_detector import detect_level_row_indices
from table1_parser.heuristics.models import RowClassification, VariableBlock
from table1_parser.heuristics.row_classifier import classify_rows, indentation_is_informative
from table1_parser.schemas import NormalizedTable, RowView
from table1_parser.text_cleaning import clean_text


def _nonempty_trailing_cell_count(row_view: RowView) -> int:
    """Count meaningful trailing cells while preserving raw row text elsewhere."""
    return sum(bool(clean_text(cell)) for cell in row_view.raw_cells[1:])


def group_variable_blocks(
    table: NormalizedTable,
    classifications: list[RowClassification] | None = None,
) -> list[VariableBlock]:
    """Group normalized body rows into candidate variables."""
    classifications = classifications or classify_rows(table)
    classifications_by_row = {
        classification.row_idx: classification.classification for classification in classifications
    }
    row_views_by_idx = {row_view.row_idx: row_view for row_view in table.row_views}
    row_order = [row_view.row_idx for row_view in table.row_views]
    use_indentation = indentation_is_informative(table)
    adjusted = dict(classifications_by_row)
    for row_idx in row_order:
        if adjusted.get(row_idx) != "continuous_variable_row":
            continue
        row_view = row_views_by_idx[row_idx]
        if _nonempty_trailing_cell_count(row_view) > 1:
            continue
        level_rows = detect_level_row_indices(
            parent_row_idx=row_idx,
            row_order=row_order,
            classifications_by_row=adjusted,
        )
        more_indented_levels = (
            sum(
                1
                for level_row_idx in level_rows
                if row_views_by_idx[level_row_idx].indent_level is not None
                and row_view.indent_level is not None
                and row_views_by_idx[level_row_idx].indent_level > row_view.indent_level
            )
            if use_indentation
            else 0
        )
        if len(level_rows) >= 2 and (
            (use_indentation and more_indented_levels >= 1)
            or _nonempty_trailing_cell_count(row_view) <= 1
        ):
            adjusted[row_idx] = "variable_header"
    classifications_by_row = adjusted
    blocks: list[VariableBlock] = []
    consumed_rows: set[int] = set()

    for row_idx in row_order:
        if row_idx in consumed_rows:
            continue

        row_view = row_views_by_idx[row_idx]
        classification = classifications_by_row.get(row_idx, "unknown")
        if classification == "continuous_variable_row":
            blocks.append(
                VariableBlock(
                    variable_row_idx=row_idx,
                    row_start=row_idx,
                    row_end=row_idx,
                    variable_label=row_view.first_cell_raw,
                    variable_kind="continuous",
                    level_row_indices=[],
                )
            )
            consumed_rows.add(row_idx)
            continue

        if classification == "variable_header":
            level_rows = detect_level_row_indices(
                parent_row_idx=row_idx,
                row_order=row_order,
                classifications_by_row=classifications_by_row,
            )
            consumed_rows.add(row_idx)
            consumed_rows.update(level_rows)
            blocks.append(
                VariableBlock(
                    variable_row_idx=row_idx,
                    row_start=row_idx,
                    row_end=level_rows[-1] if level_rows else row_idx,
                    variable_label=row_view.first_cell_raw,
                    variable_kind="categorical" if level_rows else "unknown",
                    level_row_indices=level_rows,
                )
            )
    return blocks
