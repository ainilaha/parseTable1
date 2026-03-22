"""Build deterministic TableDefinition artifacts."""

from __future__ import annotations

from table1_parser.heuristics.table_definition_columns import build_column_definition
from table1_parser.heuristics.table_definition_rows import build_defined_variables
from table1_parser.schemas import NormalizedTable, TableDefinition
from table1_parser.validation.table_definition import validate_table_definition


def build_table_definition(table: NormalizedTable) -> TableDefinition:
    """Build one deterministic TableDefinition from a normalized table."""
    variables = build_defined_variables(table)
    column_definition = build_column_definition(table)
    notes = _notes(table)
    definition = TableDefinition(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        variables=variables,
        column_definition=column_definition,
        notes=notes,
        overall_confidence=_overall_confidence(variables, column_definition),
    )
    return validate_table_definition(definition, table)


def build_table_definitions(tables: list[NormalizedTable]) -> list[TableDefinition]:
    """Build deterministic TableDefinition artifacts for a list of tables."""
    return [build_table_definition(table) for table in tables]


def table_definitions_to_payload(tables: list[TableDefinition]) -> list[dict[str, object]]:
    """Serialize TableDefinition models as JSON-friendly dictionaries."""
    return [table.model_dump(mode="json") for table in tables]


def _notes(table: NormalizedTable) -> list[str]:
    """Return simple notes carried forward from normalization metadata."""
    if table.metadata.get("table_orientation") == "rotated":
        return ["rotated_table_layout"]
    return []


def _overall_confidence(variables: list[object], column_definition: object) -> float | None:
    """Average the available component confidences."""
    confidences = [variable.confidence for variable in variables if getattr(variable, "confidence", None) is not None]
    if getattr(column_definition, "confidence", None) is not None:
        confidences.append(column_definition.confidence)
    if not confidences:
        return None
    return round(sum(confidences) / len(confidences), 4)
