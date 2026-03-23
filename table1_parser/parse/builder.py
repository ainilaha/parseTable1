"""Build final ParsedTable artifacts from normalized tables and table definitions."""

from __future__ import annotations

from table1_parser.parse.value_parser import build_value_records
from table1_parser.schemas import (
    DefinedColumn,
    DefinedVariable,
    NormalizedTable,
    ParsedColumn,
    ParsedLevel,
    ParsedTable,
    ParsedVariable,
    TableDefinition,
)
from table1_parser.validation.parsed_table import validate_parsed_table


def build_parsed_table(table: NormalizedTable, definition: TableDefinition) -> ParsedTable:
    """Build one final parsed table from a normalized table and its semantic definition."""
    variables = [_parsed_variable(variable) for variable in definition.variables]
    columns = [_parsed_column(column) for column in definition.column_definition.columns]
    values, value_notes = build_value_records(table, definition.variables, columns)
    parsed = ParsedTable(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        variables=variables,
        columns=columns,
        values=values,
        notes=[*definition.notes, *value_notes],
        overall_confidence=_overall_confidence(variables, columns, values),
    )
    return validate_parsed_table(parsed, table, definition)


def build_parsed_tables(tables: list[NormalizedTable], definitions: list[TableDefinition]) -> list[ParsedTable]:
    """Build final parsed tables while preserving input order."""
    return [
        build_parsed_table(table, definition)
        for table, definition in zip(tables, definitions, strict=True)
    ]


def parsed_tables_to_payload(tables: list[ParsedTable]) -> list[dict[str, object]]:
    """Serialize ParsedTable models as JSON-friendly dictionaries."""
    return [table.model_dump(mode="json") for table in tables]


def _parsed_variable(variable: DefinedVariable) -> ParsedVariable:
    """Convert one defined variable into the final parsed-variable shape."""
    return ParsedVariable(
        variable_name=variable.variable_name,
        variable_label=variable.variable_label,
        variable_type=variable.variable_type,
        row_start=variable.row_start,
        row_end=variable.row_end,
        levels=[ParsedLevel(label=level.level_label, row_idx=level.row_idx) for level in variable.levels],
        confidence=variable.confidence,
    )


def _parsed_column(column: DefinedColumn) -> ParsedColumn:
    """Map TableDefinition column roles onto the narrower ParsedTable vocabulary."""
    return ParsedColumn(
        col_idx=column.col_idx,
        column_name=column.column_name,
        column_label=column.column_label,
        inferred_role=_parsed_column_role(column.inferred_role),
        confidence=column.confidence,
    )


def _parsed_column_role(role: str) -> str:
    """Collapse intermediate column roles into the final parsed schema."""
    if role in {"group", "overall", "p_value", "unknown"}:
        return role
    if role in {"comparison_group"}:
        return "group"
    if role in {"smd"}:
        return "statistic"
    return "unknown"


def _overall_confidence(
    variables: list[ParsedVariable],
    columns: list[ParsedColumn],
    values: list[object],
) -> float | None:
    """Average the available variable, column, and value confidences."""
    confidences = [item.confidence for item in [*variables, *columns, *values] if getattr(item, "confidence", None) is not None]
    if not confidences:
        return None
    return round(sum(confidences) / len(confidences), 4)
