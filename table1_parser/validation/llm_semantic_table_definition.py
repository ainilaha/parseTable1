"""Validation for LLM semantic TableDefinition artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from table1_parser.schemas import (
    ColumnDefinition,
    DefinedColumn,
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
    """Validate one LLM semantic interpretation against table structure and retrieved context."""
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
        column_definition=ColumnDefinition(
            grouping_label=definition.column_definition.grouping_label,
            grouping_name=definition.column_definition.grouping_name,
            columns=[
                DefinedColumn(
                    col_idx=column.col_idx,
                    column_name=column.column_name,
                    column_label=column.column_label,
                    inferred_role=column.inferred_role,
                    grouping_variable_hint=column.grouping_variable_hint,
                    confidence=column.confidence,
                )
                for column in definition.column_definition.columns
            ],
            confidence=definition.column_definition.confidence,
        ),
        notes=list(definition.notes),
        overall_confidence=definition.overall_confidence,
    )
    validate_table_definition(projected, table)

    valid_passage_ids = {passage.passage_id for passage in context.passages}
    for variable in definition.variables:
        _require(
            all(passage_id in valid_passage_ids for passage_id in variable.evidence_passage_ids),
            f"Unknown evidence passage on variable {variable.variable_name}.",
        )
        for level in variable.levels:
            _require(
                all(passage_id in valid_passage_ids for passage_id in level.evidence_passage_ids),
                f"Unknown evidence passage on level {level.level_name}.",
            )
    _require(
        all(passage_id in valid_passage_ids for passage_id in definition.column_definition.evidence_passage_ids),
        "Unknown evidence passage on column definition.",
    )
    for column in definition.column_definition.columns:
        _require(
            all(passage_id in valid_passage_ids for passage_id in column.evidence_passage_ids),
            f"Unknown evidence passage on column {column.column_name}.",
        )
    return definition


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
