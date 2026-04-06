"""Focused tests for the narrow LLM semantic TableDefinition layer."""

from __future__ import annotations

import json

import pytest

from table1_parser.context.retrieval import build_table_context
from table1_parser.context.section_parser import parse_markdown_sections
from table1_parser.heuristics import build_table_definition
from table1_parser.llm.client import StaticStructuredLLMClient
from table1_parser.llm.semantic_parser import LLMSemanticInterpretationError, LLMSemanticTableDefinitionParser
from table1_parser.llm.semantic_prompts import (
    TABLE_DEFINITION_SEMANTIC_PROMPT,
    build_llm_semantic_input_payload,
    build_llm_semantic_prompt,
)
from table1_parser.llm.prompts import load_prompt_template
from table1_parser.llm.semantic_schemas import LLMSemanticTableDefinition
from table1_parser.schemas import NormalizedTable, RowView


def _build_row(row_idx: int, first_cell_raw: str, trailing: list[str]) -> RowView:
    raw_cells = [first_cell_raw, *trailing]
    alpha_only = " ".join(
        "".join(ch if ch.isalpha() or ch.isspace() else " " for ch in first_cell_raw).split()
    )
    return RowView(
        row_idx=row_idx,
        raw_cells=raw_cells,
        first_cell_raw=first_cell_raw,
        first_cell_normalized=first_cell_raw,
        first_cell_alpha_only=alpha_only,
        nonempty_cell_count=sum(bool(cell) for cell in raw_cells),
        numeric_cell_count=sum(any(char.isdigit() for char in cell) for cell in raw_cells),
        has_trailing_values=any(bool(cell) for cell in trailing),
        indent_level=None,
        likely_role=None,
    )


def _build_table() -> NormalizedTable:
    return NormalizedTable(
        table_id="tbl-semantic",
        title="Table 2. Baseline characteristics by DKD status",
        caption="Characteristics by DKD status",
        header_rows=[0],
        body_rows=[1, 2, 3, 4],
        row_views=[
            _build_row(1, "Age, years", ["52.3 (14.1)", "49.1 (13.2)", "<0.001"]),
            _build_row(2, "Sex", ["", "", ""]),
            _build_row(3, "Male", ["412 (48.2)", "310 (44.1)", ""]),
            _build_row(4, "Female", ["443 (51.8)", "393 (55.9)", ""]),
        ],
        n_rows=5,
        n_cols=4,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall", "DKD", "P-value"],
                ["Age, years", "52.3 (14.1)", "49.1 (13.2)", "<0.001"],
                ["Sex", "", "", ""],
                ["Male", "412 (48.2)", "310 (44.1)", ""],
                ["Female", "443 (51.8)", "393 (55.9)", ""],
            ]
        },
    )


def _build_context_and_definition() -> tuple[NormalizedTable, object, object]:
    table = _build_table()
    definition = build_table_definition(table)
    sections = parse_markdown_sections(
        "# Study Population\nAge and DKD status were measured.\n\n"
        "# Results\nTable 2 shows baseline characteristics by DKD status."
    )
    context = build_table_context(0, definition, sections)
    return table, definition, context


def test_semantic_prompt_payload_contains_compact_row_structure() -> None:
    """Semantic payload should carry compact row hints and deterministic row spans only."""
    table, definition, context = _build_context_and_definition()

    payload = build_llm_semantic_input_payload(table, definition, context)

    assert payload.body_rows[1].row_idx == 2
    assert payload.body_rows[1].label == "Sex"
    assert payload.body_rows[1].has_trailing_values is False
    assert payload.body_rows[2].numeric_cell_count == 2
    assert payload.deterministic_variables[0].label == "Age, years"
    assert payload.deterministic_variables[1].levels[0].label == "Male"
    assert payload.table_text == "Characteristics by DKD status"
    dumped = payload.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True)
    assert "rows" in dumped
    assert "vars" in dumped
    assert "deterministic_variables" not in dumped
    assert "cells" not in json.dumps(dumped)
    assert "passages" not in dumped


def test_semantic_prompt_includes_structure_and_safety_requirements() -> None:
    """The semantic prompt should explicitly require strict JSON and row-structure safety."""
    table, definition, context = _build_context_and_definition()
    payload = build_llm_semantic_input_payload(table, definition, context)

    prompt = build_llm_semantic_prompt(payload, LLMSemanticTableDefinition.model_json_schema())

    assert "Goal:" in prompt
    assert "Inputs:" in prompt
    assert "Desired outputs:" in prompt
    assert "Constraints:" in prompt
    assert "Failure modes to minimize:" in prompt
    assert "Success criteria:" in prompt
    assert "Working style:" in prompt
    assert "return strict JSON only" in prompt
    assert "inventing rows, levels, or variables" in prompt
    assert "Output schema:" in prompt
    assert "units_hint" not in prompt
    assert "summary_style_hint" not in prompt
    assert '"column_definition"' not in prompt
    assert '"rows"' in prompt
    assert '"vars"' in prompt
    assert '"passages"' not in prompt
    assert "deterministic_variables" not in prompt
    assert '"cells"' not in prompt


def test_semantic_prompt_template_is_repo_file() -> None:
    """The semantic prompt should live in a version-controlled template file."""
    template = load_prompt_template(TABLE_DEFINITION_SEMANTIC_PROMPT)

    assert "Failure modes to minimize:" in template
    assert "use only the provided `rows` and `vars`" in template
    assert "{{TABLE_PAYLOAD_JSON}}" in template
    assert "{{OUTPUT_SCHEMA_SECTION}}" in template


def test_semantic_prompt_omits_schema_section_when_not_requested() -> None:
    """Prompt builder should support provider-native structured parsing without duplicating schema text."""
    table, definition, context = _build_context_and_definition()
    payload = build_llm_semantic_input_payload(table, definition, context)

    prompt = build_llm_semantic_prompt(payload, {})

    assert "Output schema:" not in prompt


def test_semantic_parser_validates_safe_structured_response(tmp_path) -> None:
    """The semantic parser should return a typed interpretation when indices are valid."""
    table, definition, context = _build_context_and_definition()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-semantic",
            "variables": [
                {
                    "variable_name": "Age years",
                    "variable_label": "Age, years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "confidence": 0.94,
                    "disagrees_with_deterministic": False,
                },
                {
                    "variable_name": "Sex",
                    "variable_label": "Sex",
                    "variable_type": "binary",
                    "row_start": 2,
                    "row_end": 4,
                    "levels": [
                        {
                            "level_name": "Male",
                            "level_label": "Male",
                            "row_idx": 3,
                        },
                        {
                            "level_name": "Female",
                            "level_label": "Female",
                            "row_idx": 4,
                        },
                    ],
                    "confidence": 0.9,
                    "disagrees_with_deterministic": False,
                },
            ],
            "notes": ["Variable grouping is plausible."],
            "overall_confidence": 0.92,
        }
    )

    result = LLMSemanticTableDefinitionParser(client).parse(table, definition, context, trace_dir=tmp_path)

    assert result.table_id == "tbl-semantic"
    assert result.variables[1].levels[0].level_label == "Male"
    assert (tmp_path / "table_definition_llm_input.json").exists()
    assert (tmp_path / "table_definition_llm_metrics.json").exists()
    assert (tmp_path / "table_definition_llm_output.json").exists()
    assert (tmp_path / "table_definition_llm_interpretation.json").exists()

def test_semantic_parser_rejects_invalid_row_reference() -> None:
    """LLM semantic output should fail if it invents a row index."""
    table, definition, context = _build_context_and_definition()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-semantic",
            "variables": [
                {
                    "variable_name": "Bad",
                    "variable_label": "Bad",
                    "variable_type": "continuous",
                    "row_start": 99,
                    "row_end": 99,
                    "levels": [],
                }
            ],
            "notes": [],
        }
    )

    with pytest.raises(LLMSemanticInterpretationError):
        LLMSemanticTableDefinitionParser(client).parse(table, definition, context)


def test_semantic_trace_preserves_raw_response(tmp_path) -> None:
    """Trace artifacts should preserve the raw structured LLM response."""
    table, definition, context = _build_context_and_definition()
    response = {
        "table_id": "tbl-semantic",
        "variables": [],
        "notes": [],
    }
    client = StaticStructuredLLMClient(response=response)

    LLMSemanticTableDefinitionParser(client).parse(table, definition, context, trace_dir=tmp_path)

    llm_output = json.loads((tmp_path / "table_definition_llm_output.json").read_text())
    llm_metrics = json.loads((tmp_path / "table_definition_llm_metrics.json").read_text())
    assert llm_output["response"] == response
    assert llm_metrics["status"] == "success"
    assert llm_metrics["prompt_char_count"] > 0
