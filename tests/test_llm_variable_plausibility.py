"""Focused tests for the TableDefinition variable-plausibility review prompt."""

from __future__ import annotations

import json

import pytest

from table1_parser.llm.client import StaticStructuredLLMClient
from table1_parser.llm.prompts import load_prompt_template
from table1_parser.llm.variable_plausibility_parser import (
    LLMVariablePlausibilityReviewError,
    LLMVariablePlausibilityTableReviewParser,
)
from table1_parser.llm.variable_plausibility_prompts import (
    TABLE_DEFINITION_VARIABLE_PLAUSIBILITY_PROMPT,
    build_variable_plausibility_input_payload,
    build_variable_plausibility_prompt,
)
from table1_parser.llm.variable_plausibility_schemas import LLMVariablePlausibilityTableReview
from table1_parser.schemas import ColumnDefinition, DefinedLevel, DefinedVariable, TableDefinition


def _build_definition() -> TableDefinition:
    return TableDefinition(
        table_id="tbl-plausibility",
        title="Table 1. Baseline characteristics",
        caption="Baseline characteristics by smoking status",
        variables=[
            DefinedVariable(
                variable_name="Age",
                variable_label="Age, years",
                variable_type="continuous",
                row_start=1,
                row_end=1,
                units_hint="years",
                summary_style_hint="mean_sd",
                confidence=0.9,
            ),
            DefinedVariable(
                variable_name="Sex",
                variable_label="Sex",
                variable_type="categorical",
                row_start=2,
                row_end=4,
                levels=[
                    DefinedLevel(level_name="Male", level_label="Male", row_idx=3),
                    DefinedLevel(level_name="Female", level_label="Female", row_idx=4),
                ],
                summary_style_hint="count_pct",
                confidence=0.92,
            ),
            DefinedVariable(
                variable_name="Current smoker",
                variable_label="Current smoker, n (%)",
                variable_type="binary",
                row_start=5,
                row_end=5,
                summary_style_hint="count_pct",
                confidence=0.95,
            ),
        ],
        column_definition=ColumnDefinition(columns=[]),
        notes=[],
        overall_confidence=0.92,
    )


def test_variable_plausibility_payload_contains_only_variable_level_evidence() -> None:
    """The plausibility payload should carry one compact variable list and table text."""
    payload = build_variable_plausibility_input_payload(_build_definition())

    assert payload.table_text == "Baseline characteristics by smoking status"
    assert payload.variables[0].variable_type == "continuous"
    assert payload.variables[1].levels[0].level_label == "Male"
    assert payload.variables[2].summary_style_hint == "count_pct"
    dumped = payload.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True)
    dumped_json = json.dumps(dumped, sort_keys=True)
    assert "vars" in dumped
    assert "variables" not in dumped
    assert dumped["vars"][0]["type"] == "continuous"
    assert dumped["vars"][1]["levels"][1]["level_label"] == "Female"
    assert '"column_definition"' not in dumped_json
    assert '"confidence"' not in dumped_json


def test_variable_plausibility_prompt_includes_scoring_and_safety_requirements() -> None:
    """The prompt should describe the scoring rubric and forbid variable invention or rewriting."""
    payload = build_variable_plausibility_input_payload(_build_definition())

    prompt = build_variable_plausibility_prompt(payload, LLMVariablePlausibilityTableReview.model_json_schema())

    assert "You are reviewing an epidemiology paper" in prompt
    assert "Table 1 describes the demographics, baseline characteristics, exposures, covariates" in prompt
    assert "pay special attention to categorical levels" in prompt
    assert "age, sex, race/ethnicity, smoking, BMI" in prompt
    assert "Scoring rubric:" in prompt
    assert "Type-specific guidance:" in prompt
    assert "judge whether each supplied variable looks semantically plausible for a Table 1-style epidemiology table" not in prompt
    assert "must be a single-row variable and must not have child levels" in prompt
    assert "a categorical variable must have one or more child levels" in prompt
    assert "should be a one-row indicator variable with no child levels" in prompt
    assert "Secondary evidence:" in prompt
    assert "return the same variables in the same order" in prompt
    assert "do not invent, remove, split, merge, or rename variables" in prompt
    assert "do not invent, remove, reorder, or rename levels" in prompt
    assert "a continuous variable has children, a categorical variable has no children, or a binary variable has children" in prompt
    assert "add one `plausibility_score` between `0` and `1` for each variable" in prompt
    assert "Output schema:" in prompt
    assert '"vars"' in prompt
    assert '"column_definition"' not in prompt
    assert '"confidence"' not in prompt


def test_variable_plausibility_prompt_template_is_repo_file() -> None:
    """The variable-plausibility prompt should live in a version-controlled template file."""
    template = load_prompt_template(TABLE_DEFINITION_VARIABLE_PLAUSIBILITY_PROMPT)

    assert "You are reviewing an epidemiology paper" in template
    assert "Domain expectations:" in template
    assert "Scoring rubric:" in template
    assert "a categorical variable must have one or more child levels" in template
    assert "do not invent, remove, split, merge, or rename variables" in template
    assert "{{TABLE_PAYLOAD_JSON}}" in template
    assert "{{OUTPUT_SCHEMA_SECTION}}" in template


def test_variable_plausibility_prompt_omits_schema_section_when_not_requested() -> None:
    """Prompt builder should support providers with native structured-output parsing."""
    payload = build_variable_plausibility_input_payload(_build_definition())

    prompt = build_variable_plausibility_prompt(payload, {})

    assert "Output schema:" not in prompt


def test_variable_plausibility_review_schema_accepts_scored_variable_list() -> None:
    """The review schema should validate a variable list with per-variable plausibility scores."""
    review = LLMVariablePlausibilityTableReview.model_validate(
        {
            "table_id": "tbl-plausibility",
            "variables": [
                {
                    "variable_name": "Age",
                    "variable_label": "Age, years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "units_hint": "years",
                    "summary_style_hint": "mean_sd",
                    "plausibility_score": 0.98,
                },
                {
                    "variable_name": "Sex",
                    "variable_label": "Sex",
                    "variable_type": "categorical",
                    "row_start": 2,
                    "row_end": 4,
                    "levels": [
                        {"level_name": "Male", "level_label": "Male", "row_idx": 3},
                        {"level_name": "Female", "level_label": "Female", "row_idx": 4},
                    ],
                    "summary_style_hint": "count_pct",
                    "plausibility_score": 0.97,
                },
            ],
            "notes": ["Both variables look semantically coherent."],
            "overall_plausibility": 0.975,
        }
    )

    assert review.variables[0].plausibility_score == 0.98
    assert review.variables[1].levels[1].level_label == "Female"


def test_variable_plausibility_parser_validates_safe_structured_response(tmp_path) -> None:
    """The plausibility parser should return a typed review when identities are preserved."""
    definition = _build_definition()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-plausibility",
            "variables": [
                {
                    "variable_name": "Age",
                    "variable_label": "Age, years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "units_hint": "years",
                    "summary_style_hint": "mean_sd",
                    "plausibility_score": 0.99,
                },
                {
                    "variable_name": "Sex",
                    "variable_label": "Sex",
                    "variable_type": "categorical",
                    "row_start": 2,
                    "row_end": 4,
                    "levels": [
                        {"level_name": "Male", "level_label": "Male", "row_idx": 3},
                        {"level_name": "Female", "level_label": "Female", "row_idx": 4},
                    ],
                    "units_hint": None,
                    "summary_style_hint": "count_pct",
                    "plausibility_score": 0.97,
                    "plausibility_note": None,
                },
                {
                    "variable_name": "Current smoker",
                    "variable_label": "Current smoker, n (%)",
                    "variable_type": "binary",
                    "row_start": 5,
                    "row_end": 5,
                    "levels": [],
                    "units_hint": None,
                    "summary_style_hint": "count_pct",
                    "plausibility_score": 0.9,
                    "plausibility_note": "Single-row binary indicator is plausible.",
                },
            ],
            "notes": ["All variables look semantically coherent."],
            "overall_plausibility": 0.953,
        }
    )

    result = LLMVariablePlausibilityTableReviewParser(client).review(
        definition,
        table_index=0,
        table_family="descriptive_characteristics",
        trace_dir=tmp_path,
    )

    assert result.table_id == "tbl-plausibility"
    assert result.variables[1].levels[0].level_label == "Male"
    assert (tmp_path / "variable_plausibility_llm_input.json").exists()
    assert (tmp_path / "variable_plausibility_llm_metrics.json").exists()
    assert (tmp_path / "variable_plausibility_llm_output.json").exists()
    assert (tmp_path / "variable_plausibility_llm_review.json").exists()


def test_variable_plausibility_parser_rejects_identity_changes() -> None:
    """The plausibility parser should fail if the review rewrites a variable identity field."""
    definition = _build_definition()
    client = StaticStructuredLLMClient(
        response={
            "table_id": "tbl-plausibility",
            "variables": [
                {
                    "variable_name": "Age",
                    "variable_label": "Age, years",
                    "variable_type": "continuous",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [],
                    "units_hint": "years",
                    "summary_style_hint": "mean_sd",
                    "plausibility_score": 0.99,
                },
                {
                    "variable_name": "Sex rewritten",
                    "variable_label": "Sex",
                    "variable_type": "categorical",
                    "row_start": 2,
                    "row_end": 4,
                    "levels": [
                        {"level_name": "Male", "level_label": "Male", "row_idx": 3},
                        {"level_name": "Female", "level_label": "Female", "row_idx": 4},
                    ],
                    "summary_style_hint": "count_pct",
                    "plausibility_score": 0.97,
                },
                {
                    "variable_name": "Current smoker",
                    "variable_label": "Current smoker, n (%)",
                    "variable_type": "binary",
                    "row_start": 5,
                    "row_end": 5,
                    "levels": [],
                    "summary_style_hint": "count_pct",
                    "plausibility_score": 0.9,
                },
            ],
            "notes": [],
        }
    )

    with pytest.raises(LLMVariablePlausibilityReviewError):
        LLMVariablePlausibilityTableReviewParser(client).review(
            definition,
            table_index=0,
            table_family="descriptive_characteristics",
        )


def test_variable_plausibility_trace_preserves_raw_response(tmp_path) -> None:
    """Trace artifacts should preserve the raw structured variable-plausibility response."""
    definition = _build_definition()
    response = {
        "table_id": "tbl-plausibility",
        "variables": [
            {
                "variable_name": "Age",
                "variable_label": "Age, years",
                "variable_type": "continuous",
                "row_start": 1,
                "row_end": 1,
                "levels": [],
                "units_hint": "years",
                "summary_style_hint": "mean_sd",
                "plausibility_score": 0.99,
            },
            {
                "variable_name": "Sex",
                "variable_label": "Sex",
                "variable_type": "categorical",
                "row_start": 2,
                "row_end": 4,
                "levels": [
                    {"level_name": "Male", "level_label": "Male", "row_idx": 3},
                    {"level_name": "Female", "level_label": "Female", "row_idx": 4},
                ],
                "units_hint": None,
                "summary_style_hint": "count_pct",
                "plausibility_score": 0.97,
            },
            {
                "variable_name": "Current smoker",
                "variable_label": "Current smoker, n (%)",
                "variable_type": "binary",
                "row_start": 5,
                "row_end": 5,
                "levels": [],
                "units_hint": None,
                "summary_style_hint": "count_pct",
                "plausibility_score": 0.9,
            },
        ],
        "notes": [],
    }
    client = StaticStructuredLLMClient(response=response)

    LLMVariablePlausibilityTableReviewParser(client).review(
        definition,
        table_index=0,
        table_family="descriptive_characteristics",
        trace_dir=tmp_path,
    )

    llm_output = json.loads((tmp_path / "variable_plausibility_llm_output.json").read_text())
    llm_metrics = json.loads((tmp_path / "variable_plausibility_llm_metrics.json").read_text())
    assert llm_output["response"] == response
    assert llm_metrics["status"] == "success"
    assert llm_metrics["prompt_char_count"] > 0
