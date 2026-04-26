"""Prompt helpers for TableDefinition variable-plausibility review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from table1_parser.llm.prompts import load_prompt_template, merge_prompt_table_text, render_prompt_template
from table1_parser.llm.variable_plausibility_schemas import (
    LLMVariablePlausibilityInputPayload,
    LLMVariablePlausibilityLevelPayload,
    LLMVariablePlausibilityVariablePayload,
)
from table1_parser.schemas import TableDefinition
from table1_parser.text_cleaning import clean_text


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
TABLE_DEFINITION_VARIABLE_PLAUSIBILITY_PROMPT = PROMPTS_DIR / "table_definition_variable_plausibility_prompt.md"


def build_variable_plausibility_input_payload(definition: TableDefinition) -> LLMVariablePlausibilityInputPayload:
    """Build the compact variable-only payload supplied to the plausibility-review prompt."""
    return LLMVariablePlausibilityInputPayload(
        table_id=definition.table_id,
        table_text=merge_prompt_table_text(definition.title, definition.caption),
        variables=[
            LLMVariablePlausibilityVariablePayload(
                variable_name=clean_text(variable.variable_name) or variable.variable_name,
                variable_label=clean_text(variable.variable_label) or variable.variable_label,
                variable_type=variable.variable_type,
                row_start=variable.row_start,
                row_end=variable.row_end,
                levels=[
                    LLMVariablePlausibilityLevelPayload(
                        row_idx=level.row_idx,
                        level_name=clean_text(level.level_name) or level.level_name,
                        level_label=clean_text(level.level_label) or level.level_label,
                    )
                    for level in variable.levels
                ],
                units_hint=clean_text(variable.units_hint) if variable.units_hint else None,
                summary_style_hint=variable.summary_style_hint,
            )
            for variable in definition.variables
        ],
    )


def build_variable_plausibility_prompt(
    payload: LLMVariablePlausibilityInputPayload,
    output_schema: dict[str, Any],
) -> str:
    """Build a strict JSON-only prompt for per-variable plausibility review."""
    template = load_prompt_template(TABLE_DEFINITION_VARIABLE_PLAUSIBILITY_PROMPT)
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
