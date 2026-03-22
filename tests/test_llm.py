"""Focused tests for the Phase 5 LLM-assisted interpretation layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from table1_parser.llm.client import StaticStructuredLLMClient
from table1_parser.llm.parser import LLMInterpretationError, LLMTableParser
from table1_parser.llm.prompts import (
    TABLE_INTERPRETATION_PROMPT,
    build_llm_input_payload,
    build_llm_prompt,
    load_prompt_template,
    render_prompt_template,
)
from table1_parser.llm.schemas import LLMInputPayload, LLMTableInterpretation
from table1_parser.schemas import NormalizedTable, RowView


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "table_llm_payload.schema.json"
SAMPLE_PAYLOAD_PATH = REPO_ROOT / "tests" / "data" / "sample_table_llm_payload.json"


def _build_row(
    row_idx: int,
    first_cell_raw: str,
    trailing: list[str],
) -> RowView:
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
        table_id="tbl-llm",
        title="Table 1. Baseline characteristics",
        caption="Characteristics by diabetes status",
        header_rows=[0],
        body_rows=[1, 2, 3, 4],
        row_views=[
            _build_row(1, "Age, years", ["52.3 (14.1)", "49.1 (13.2)", "61.8 (11.3)", "<0.001"]),
            _build_row(2, "Sex", ["", "", "", ""]),
            _build_row(3, "Male", ["412 (48.2)", "310 (44.1)", "102 (60.7)", ""]),
            _build_row(4, "Female", ["443 (51.8)", "393 (55.9)", "50 (39.3)", ""]),
        ],
        n_rows=5,
        n_cols=5,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall", "No diabetes", "Diabetes", "P-value"],
                ["Age, years", "52.3 (14.1)", "49.1 (13.2)", "61.8 (11.3)", "<0.001"],
                ["Sex", "", "", "", ""],
                ["Male", "412 (48.2)", "310 (44.1)", "102 (60.7)", ""],
                ["Female", "443 (51.8)", "393 (55.9)", "50 (39.3)", ""],
            ]
        },
    )


def test_prompt_payload_contains_normalized_rows_and_heuristics() -> None:
    """Prompt payload should stay compact and structured around normalized and heuristic state."""
    table = _build_table()
    payload = build_llm_input_payload(
        table=table,
        row_classifications=[],
        variable_blocks=[],
        column_roles=[],
    )

    assert payload.title == "Table 1. Baseline characteristics"
    assert payload.header_rows[0][0] == "Characteristic"
    assert payload.body_rows[1][0] == "Sex"
    assert payload.heuristics.row_classifications == []


def test_prompt_includes_strict_json_only_instructions() -> None:
    """Prompt text should explicitly constrain the LLM to the supplied structure."""
    table = _build_table()
    payload = build_llm_input_payload(table, [], [], [])
    prompt = build_llm_prompt(payload, LLMTableInterpretation.model_json_schema())

    assert "Return strict JSON only." in prompt
    assert "Do not invent rows, columns, levels, or variables." in prompt
    assert '"table_id": "tbl-llm"' in prompt


def test_prompt_template_is_loaded_from_repository_file() -> None:
    """The Phase 5 prompt text should live in a version-controlled template file."""
    template = load_prompt_template(TABLE_INTERPRETATION_PROMPT)

    assert "Return strict JSON only." in template
    assert "{{TABLE_PAYLOAD_JSON}}" in template
    assert "{{OUTPUT_SCHEMA_JSON}}" in template


def test_prompt_template_rendering_replaces_placeholders() -> None:
    """Template rendering should perform simple placeholder substitution only."""
    rendered = render_prompt_template(
        "payload={{TABLE_PAYLOAD_JSON}}\nschema={{OUTPUT_SCHEMA_JSON}}",
        {"TABLE_PAYLOAD_JSON": '{"a": 1}', "OUTPUT_SCHEMA_JSON": '{"b": 2}'},
    )

    assert rendered == 'payload={"a": 1}\nschema={"b": 2}'


def test_checked_in_llm_input_schema_matches_model_json_schema() -> None:
    """The committed JSON schema should stay in sync with the current Pydantic model."""
    checked_in_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert checked_in_schema == LLMInputPayload.model_json_schema()


def test_sample_llm_payload_validates_against_current_model() -> None:
    """The committed sample payload should match the current LLM input contract."""
    payload = json.loads(SAMPLE_PAYLOAD_PATH.read_text(encoding="utf-8"))

    parsed = LLMInputPayload.model_validate(payload)

    assert parsed.table_id == "tbl-sample"
    assert parsed.body_rows[0][0] == "n"
    assert parsed.heuristics.row_classifications[2]["classification"] == "variable_header"


def test_llm_parser_validates_structured_response() -> None:
    """The parser should return a typed interpretation when the client responds with valid JSON."""
    table = _build_table()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-llm",
            "variables": [
                {
                    "variable_name": "age_years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "confidence": 0.93,
                },
                {
                    "variable_name": "sex",
                    "variable_type": "categorical",
                    "row_start": 2,
                    "row_end": 4,
                    "levels": [
                        {"label": "Male", "row_idx": 3},
                        {"label": "Female", "row_idx": 4},
                    ],
                    "confidence": 0.9,
                },
            ],
            "columns": [
                {"col_idx": 1, "column_name": "overall", "inferred_role": "overall", "confidence": 0.95},
                {"col_idx": 4, "column_name": "p_value", "inferred_role": "p_value", "confidence": 0.98},
            ],
            "notes": ["Conservative interpretation."],
        }
    )

    result = LLMTableParser(client).parse(table)

    assert result.table_id == "tbl-llm"
    assert result.variables[1].levels[0].label == "Male"
    assert result.columns[1].inferred_role == "p_value"
    assert client.calls


def test_llm_parser_raises_structured_error_on_invalid_response() -> None:
    """Malformed structured output should fail safely instead of being silently accepted."""
    table = _build_table()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-llm",
            "variables": [{"variable_name": "age_years"}],
            "columns": [],
            "notes": [],
        }
    )

    with pytest.raises(LLMInterpretationError) as exc_info:
        LLMTableParser(client).parse(table)

    assert exc_info.value.payload is not None
    assert exc_info.value.raw_response is not None


def test_llm_parser_writes_trace_artifacts_when_enabled(tmp_path) -> None:
    """Debug trace mode should write the expected artifact files."""
    table = _build_table()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-llm",
            "variables": [
                {
                    "variable_name": "age_years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "confidence": 0.93,
                }
            ],
            "columns": [
                {"col_idx": 1, "column_name": "overall", "inferred_role": "overall", "confidence": 0.95},
            ],
            "notes": ["Reviewed by LLM."],
        }
    )

    LLMTableParser(client).parse(table, trace_dir=tmp_path)

    assert (tmp_path / "heuristics.json").exists()
    assert (tmp_path / "llm_input.json").exists()
    assert (tmp_path / "llm_output.json").exists()
    assert (tmp_path / "final_interpretation.json").exists()
    assert (tmp_path / "diff.txt").exists()


def test_llm_parser_trace_preserves_heuristics_and_llm_output(tmp_path) -> None:
    """Trace artifacts should preserve the pre-LLM heuristic state and raw LLM response."""
    table = _build_table()
    response = {
        "table_id": "tbl-llm",
        "variables": [
            {
                "variable_name": "age_years",
                "variable_type": "continuous",
                "row_start": 1,
                "row_end": 1,
                "levels": [],
                "confidence": 0.93,
            }
        ],
        "columns": [],
        "notes": [],
    }
    client = StaticStructuredLLMClient(response=response)

    LLMTableParser(client).parse(table, trace_dir=tmp_path)

    heuristics = json.loads((tmp_path / "heuristics.json").read_text())
    llm_output = json.loads((tmp_path / "llm_output.json").read_text())

    assert heuristics["row_classifications"]
    assert heuristics["variables"]
    assert llm_output["response"] == response


def test_llm_parser_trace_diff_reports_changed_fields(tmp_path) -> None:
    """The human-readable diff should surface at least one heuristic-to-LLM change."""
    table = _build_table()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-llm",
            "variables": [
                {
                    "variable_name": "age_years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "confidence": 0.93,
                },
                {
                    "variable_name": "sex_binary",
                    "variable_type": "binary",
                    "row_start": 2,
                    "row_end": 4,
                    "levels": [
                        {"label": "Male", "row_idx": 3},
                        {"label": "Female", "row_idx": 4},
                    ],
                    "confidence": 0.9,
                },
            ],
            "columns": [
                {"col_idx": 1, "column_name": "overall", "inferred_role": "overall", "confidence": 0.95},
                {"col_idx": 4, "column_name": "p_value", "inferred_role": "p_value", "confidence": 0.98},
            ],
            "notes": ["Conservative interpretation."],
        }
    )

    LLMTableParser(client).parse(table, trace_dir=tmp_path)
    diff_text = (tmp_path / "diff.txt").read_text()

    assert "variable type changed" in diff_text or "column role changed" in diff_text or "notes added" in diff_text


def test_llm_parser_trace_includes_timestamp(tmp_path) -> None:
    """Each trace artifact should include a UTC ISO-style timestamp."""
    table = _build_table()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-llm",
            "variables": [],
            "columns": [],
            "notes": [],
        }
    )

    LLMTableParser(client).parse(table, trace_dir=tmp_path)
    heuristics = json.loads((tmp_path / "heuristics.json").read_text())
    diff_text = (tmp_path / "diff.txt").read_text()

    assert heuristics["report_timestamp"].endswith("Z")
    assert "timestamp:" in diff_text
