"""Validation for deterministic TableDefinition artifacts."""

from __future__ import annotations

from table1_parser.schemas import NormalizedTable, TableDefinition


def validate_table_definition(definition: TableDefinition, table: NormalizedTable) -> TableDefinition:
    """Validate one TableDefinition against its normalized source table."""
    row_indices = set(range(table.n_rows))
    body_rows = set(table.body_rows)
    seen_columns: set[int] = set()
    for variable in definition.variables:
        _require(variable.row_start in row_indices, f"Variable row_start out of range: {variable.row_start}")
        _require(variable.row_end in row_indices, f"Variable row_end out of range: {variable.row_end}")
        _require(variable.row_start <= variable.row_end, "Variable row_start must be <= row_end.")
        _require(variable.row_start in body_rows, f"Variable row_start not in body rows: {variable.row_start}")
        for level in variable.levels:
            _require(level.row_idx in row_indices, f"Level row_idx out of range: {level.row_idx}")
            _require(level.row_idx in body_rows, f"Level row_idx not in body rows: {level.row_idx}")
            _require(variable.row_start <= level.row_idx <= variable.row_end, "Level row_idx outside variable span.")
    for column in definition.column_definition.columns:
        _require(0 <= column.col_idx < table.n_cols, f"Column col_idx out of range: {column.col_idx}")
        _require(column.col_idx not in seen_columns, f"Duplicate column col_idx: {column.col_idx}")
        seen_columns.add(column.col_idx)
    return definition


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
