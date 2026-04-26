"""Prompt helpers for row-focused LLM semantic interpretation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from table1_parser.llm.prompts import load_prompt_template, merge_prompt_table_text, render_prompt_template
from table1_parser.llm.semantic_schemas import (
    LLMDeterministicVariablePayload,
    LLMIndexedLevelPayload,
    LLMIndexedRowPayload,
    LLMSemanticInputPayload,
)
from table1_parser.schemas import NormalizedTable, TableContext, TableDefinition
from table1_parser.text_cleaning import clean_text


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
TABLE_DEFINITION_SEMANTIC_PROMPT = PROMPTS_DIR / "table_definition_semantic_prompt.md"


def build_llm_semantic_input_payload(
    table: NormalizedTable,
    deterministic_table_definition: TableDefinition,
    retrieved_context: TableContext,
) -> LLMSemanticInputPayload:
    """Build the row-focused semantic payload supplied to the LLM."""
    del retrieved_context
    row_view_by_idx = {row_view.row_idx: row_view for row_view in table.row_views}
    return LLMSemanticInputPayload(
        table_id=table.table_id,
        table_text=merge_prompt_table_text(table.title, table.caption),
        body_rows=_indexed_rows(table, row_view_by_idx),
        deterministic_variables=[
            LLMDeterministicVariablePayload(
                label=variable.variable_label,
                variable_type=variable.variable_type,
                row_start=variable.row_start,
                row_end=variable.row_end,
                levels=[
                    LLMIndexedLevelPayload(
                        row_idx=level.row_idx,
                        label=level.level_label,
                    )
                    for level in variable.levels
                ],
            )
            for variable in deterministic_table_definition.variables
        ],
    )


def build_llm_semantic_prompt(payload: LLMSemanticInputPayload, output_schema: dict[str, Any]) -> str:
    """Build a strict JSON-only prompt for semantic TableDefinition interpretation."""
    template = load_prompt_template(TABLE_DEFINITION_SEMANTIC_PROMPT)
    payload_json = json.dumps(
        payload.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True),
        separators=(",", ":"),
        sort_keys=True,
    )
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


def _indexed_rows(table: NormalizedTable, row_view_by_idx: dict[int, object]) -> list[LLMIndexedRowPayload]:
    """Build compact row hints from normalized body rows."""
    cleaned_rows = table.metadata.get("cleaned_rows", [])
    if not isinstance(cleaned_rows, list):
        cleaned_rows = []
    return [
        LLMIndexedRowPayload(
            row_idx=row_idx,
            label=_row_label(cleaned_rows, row_idx, row_view_by_idx),
            has_trailing_values=getattr(row_view_by_idx.get(row_idx), "has_trailing_values", False),
            numeric_cell_count=getattr(row_view_by_idx.get(row_idx), "numeric_cell_count", 0),
            indent_level=getattr(row_view_by_idx.get(row_idx), "indent_level", 0) or 0,
        )
        for row_idx in table.body_rows
        if _row_label(cleaned_rows, row_idx, row_view_by_idx)
    ]


def _row_label(cleaned_rows: list[object], row_idx: int, row_view_by_idx: dict[int, object]) -> str:
    """Return the best available compact label for one row."""
    if row_idx < len(cleaned_rows) and isinstance(cleaned_rows[row_idx], list) and cleaned_rows[row_idx]:
        label = clean_text(str(cleaned_rows[row_idx][0]))
        if label:
            return label
    row_view = row_view_by_idx.get(row_idx)
    if row_view is None:
        return ""
    return clean_text(getattr(row_view, "first_cell_normalized", "") or getattr(row_view, "first_cell_raw", ""))
