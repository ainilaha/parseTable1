"""Group normalized rows into deterministic candidate variable blocks."""

from __future__ import annotations

from table1_parser.heuristics.level_detector import detect_level_row_indices
from table1_parser.heuristics.models import RowClassification, VariableBlock
from table1_parser.heuristics.row_classifier import classify_rows
from table1_parser.schemas import NormalizedTable


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
    blocks: list[VariableBlock] = []
    consumed_rows: set[int] = set()

    for classification in classifications:
        row_idx = classification.row_idx
        if row_idx in consumed_rows:
            continue

        row_view = row_views_by_idx[row_idx]
        if classification.classification == "continuous_variable_row":
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

        if classification.classification == "variable_header":
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
