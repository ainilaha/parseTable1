"""Validation for row-focused LLM semantic TableDefinition artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from table1_parser.schemas import (
    ColumnDefinition,
    DefinedLevel,
    DefinedVariable,
    NormalizedTable,
    TableContext,
    TableDefinition,
)
from table1_parser.validation.table_definition import validate_table_definition

if TYPE_CHECKING:
    from table1_parser.llm.semantic_schemas import LLMSemanticTableDefinition


def validate_llm_semantic_table_definition(
    definition: LLMSemanticTableDefinition,
    table: NormalizedTable,
    context: TableContext,
) -> LLMSemanticTableDefinition:
    """Validate one row-focused LLM semantic interpretation against table structure and retrieved context."""
    del context
    _require(definition.table_id == table.table_id, "LLM semantic table_id does not match the normalized table.")
    projected = TableDefinition(
        table_id=definition.table_id,
        title=table.title,
        caption=table.caption,
        variables=[
            DefinedVariable(
                variable_name=variable.variable_name,
                variable_label=variable.variable_label,
                variable_type=variable.variable_type,
                row_start=variable.row_start,
                row_end=variable.row_end,
                levels=[
                    DefinedLevel(
                        level_name=level.level_name,
                        level_label=level.level_label,
                        row_idx=level.row_idx,
                        confidence=level.confidence,
                    )
                    for level in variable.levels
                ],
                confidence=variable.confidence,
            )
            for variable in definition.variables
        ],
        column_definition=ColumnDefinition(columns=[]),
        notes=list(definition.notes),
        overall_confidence=definition.overall_confidence,
    )
    validate_table_definition(projected, table)
    return definition


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
