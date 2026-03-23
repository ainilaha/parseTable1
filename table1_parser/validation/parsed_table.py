"""Validation for final ParsedTable artifacts."""

from __future__ import annotations

from table1_parser.schemas import NormalizedTable, ParsedTable, TableDefinition


def validate_parsed_table(parsed: ParsedTable, table: NormalizedTable, definition: TableDefinition) -> ParsedTable:
    """Validate one final parsed table against its normalized source and semantic definition."""
    row_indices = set(range(table.n_rows))
    body_rows = set(table.body_rows)
    variable_names = {variable.variable_name for variable in definition.variables}
    valid_columns = {column.col_idx for column in definition.column_definition.columns}
    valid_level_rows = {
        (variable.variable_name, level.row_idx, level.level_label)
        for variable in definition.variables
        for level in variable.levels
    }

    for variable in parsed.variables:
        _require(variable.variable_name in variable_names, f"Unknown parsed variable_name: {variable.variable_name}")
        _require(variable.row_start in row_indices, f"Parsed variable row_start out of range: {variable.row_start}")
        _require(variable.row_end in row_indices, f"Parsed variable row_end out of range: {variable.row_end}")
        for level in variable.levels:
            _require(level.row_idx in body_rows, f"Parsed level row_idx not in body rows: {level.row_idx}")

    for column in parsed.columns:
        _require(column.col_idx in valid_columns, f"Parsed column col_idx absent from TableDefinition: {column.col_idx}")

    for value in parsed.values:
        _require(value.row_idx in body_rows, f"Parsed value row_idx not in body rows: {value.row_idx}")
        _require(value.col_idx in valid_columns, f"Parsed value col_idx absent from TableDefinition: {value.col_idx}")
        _require(value.variable_name in variable_names, f"Parsed value variable_name is unknown: {value.variable_name}")
        if value.level_label is not None:
            _require(
                (value.variable_name, value.row_idx, value.level_label) in valid_level_rows,
                "Parsed value level row does not match the TableDefinition.",
            )
    return parsed


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
