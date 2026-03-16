"""Prompt-building helpers for LLM-assisted table interpretation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from table1_parser.heuristics.models import ColumnRoleGuess, RowClassification, VariableBlock
from table1_parser.llm.schemas import LLMHeuristicPayload, LLMInputPayload
from table1_parser.schemas import NormalizedTable


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
TABLE_INTERPRETATION_PROMPT = PROMPTS_DIR / "table_interpretation_prompt.md"


def build_llm_input_payload(
    table: NormalizedTable,
    row_classifications: list[RowClassification],
    variable_blocks: list[VariableBlock],
    column_roles: list[ColumnRoleGuess],
) -> LLMInputPayload:
    """Create the compact structured payload supplied to the LLM."""
    cleaned_rows = table.metadata.get("cleaned_rows", [])
    header_rows = [
        cleaned_rows[row_idx]
        for row_idx in table.header_rows
        if isinstance(cleaned_rows, list) and row_idx < len(cleaned_rows)
    ]
    body_rows = [
        cleaned_rows[row_idx]
        for row_idx in table.body_rows
        if isinstance(cleaned_rows, list) and row_idx < len(cleaned_rows)
    ]
    heuristics = LLMHeuristicPayload(
        row_classifications=[
            {
                "row_idx": item.row_idx,
                "classification": item.classification,
                "confidence": item.confidence,
            }
            for item in row_classifications
        ],
        variable_blocks=[
            {
                "variable_row_idx": block.variable_row_idx,
                "row_start": block.row_start,
                "row_end": block.row_end,
                "variable_label": block.variable_label,
                "variable_kind": block.variable_kind,
                "level_row_indices": block.level_row_indices,
            }
            for block in variable_blocks
        ],
        column_roles=[
            {
                "col_idx": role.col_idx,
                "header_label": role.header_label,
                "role": role.role,
                "confidence": role.confidence,
            }
            for role in column_roles
        ],
    )
    return LLMInputPayload(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        header_rows=header_rows,
        body_rows=body_rows,
        heuristics=heuristics,
    )


@lru_cache(maxsize=None)
def load_prompt_template(path: str | Path) -> str:
    """Load a prompt template from disk with simple in-process caching."""
    return Path(path).read_text(encoding="utf-8")


def render_prompt_template(template: str, substitutions: dict[str, str]) -> str:
    """Render a prompt template with simple placeholder substitution."""
    rendered = template
    for key, value in substitutions.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def build_llm_prompt(payload: LLMInputPayload, output_schema: dict[str, Any]) -> str:
    """Build a strict JSON-only prompt from the structured payload."""
    template = load_prompt_template(TABLE_INTERPRETATION_PROMPT)
    return render_prompt_template(
        template,
        {
            "TABLE_PAYLOAD_JSON": json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True),
            "OUTPUT_SCHEMA_JSON": json.dumps(output_schema, indent=2, sort_keys=True),
        },
    )
