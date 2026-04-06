"""Prompt helpers for row-focused LLM semantic interpretation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from table1_parser.llm.prompts import load_prompt_template, render_prompt_template
from table1_parser.llm.semantic_schemas import LLMIndexedRowPayload, LLMSemanticInputPayload
from table1_parser.schemas import (
    DefinedLevel,
    DefinedVariable,
    NormalizedTable,
    TableContext,
    TableDefinition,
)


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
TABLE_DEFINITION_SEMANTIC_PROMPT = PROMPTS_DIR / "table_definition_semantic_prompt.md"


def build_llm_semantic_input_payload(
    table: NormalizedTable,
    deterministic_table_definition: TableDefinition,
    retrieved_context: TableContext,
) -> LLMSemanticInputPayload:
    """Build the row-focused semantic payload supplied to the LLM."""
    cleaned_rows = table.metadata.get("cleaned_rows", [])
    body_rows = _indexed_rows(cleaned_rows, table.body_rows)
    return LLMSemanticInputPayload(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        body_rows=body_rows,
        deterministic_variables=[
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
            for variable in deterministic_table_definition.variables
        ],
        retrieved_passages=list(retrieved_context.passages),
    )


def build_llm_semantic_prompt(payload: LLMSemanticInputPayload, output_schema: dict[str, Any]) -> str:
    """Build a strict JSON-only prompt for semantic TableDefinition interpretation."""
    template = load_prompt_template(TABLE_DEFINITION_SEMANTIC_PROMPT)
    payload_json = json.dumps(payload.model_dump(mode="json", exclude_none=True), separators=(",", ":"), sort_keys=True)
    output_schema_section = ""
    if output_schema:
        output_schema_section = "Output schema:\n" + json.dumps(output_schema, separators=(",", ":"), sort_keys=True)
    return render_prompt_template(
        template,
        {
            "TABLE_PAYLOAD_JSON": payload_json,
            "OUTPUT_SCHEMA_SECTION": output_schema_section,
        },
    )


def _indexed_rows(cleaned_rows: object, row_indices: list[int]) -> list[LLMIndexedRowPayload]:
    """Build compact indexed row payloads from normalized cleaned rows."""
    if not isinstance(cleaned_rows, list):
        return []
    return [
        LLMIndexedRowPayload(row_idx=row_idx, cells=cleaned_rows[row_idx])
        for row_idx in row_indices
        if row_idx < len(cleaned_rows) and isinstance(cleaned_rows[row_idx], list)
    ]
