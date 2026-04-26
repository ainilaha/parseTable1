"""Validation for TableDefinition variable-plausibility review artifacts."""

from __future__ import annotations

from table1_parser.llm.variable_plausibility_schemas import (
    LLMVariablePlausibilityInputPayload,
    LLMVariablePlausibilityLevelPayload,
    LLMVariablePlausibilityTableReview,
    LLMVariablePlausibilityVariablePayload,
)


def validate_llm_variable_plausibility_review(
    review: LLMVariablePlausibilityTableReview,
    payload: LLMVariablePlausibilityInputPayload,
) -> LLMVariablePlausibilityTableReview:
    """Validate one variable-plausibility review against the exact prompt payload."""
    _require(review.table_id == payload.table_id, "LLM variable-plausibility table_id does not match the prompt payload.")
    _require(
        len(review.variables) == len(payload.variables),
        "LLM variable-plausibility review changed the number of variables.",
    )
    for expected_variable, reviewed_variable in zip(payload.variables, review.variables, strict=True):
        _validate_variable_identity(reviewed_variable, expected_variable)
    return review


def _validate_variable_identity(
    reviewed_variable: object,
    expected_variable: LLMVariablePlausibilityVariablePayload,
) -> None:
    """Require the reviewed variable to preserve all prompt-supplied identity fields exactly."""
    _require(
        getattr(reviewed_variable, "variable_name", None) == expected_variable.variable_name,
        "LLM variable-plausibility review changed variable_name.",
    )
    _require(
        getattr(reviewed_variable, "variable_label", None) == expected_variable.variable_label,
        "LLM variable-plausibility review changed variable_label.",
    )
    _require(
        getattr(reviewed_variable, "variable_type", None) == expected_variable.variable_type,
        "LLM variable-plausibility review changed variable_type.",
    )
    _require(
        getattr(reviewed_variable, "row_start", None) == expected_variable.row_start,
        "LLM variable-plausibility review changed row_start.",
    )
    _require(
        getattr(reviewed_variable, "row_end", None) == expected_variable.row_end,
        "LLM variable-plausibility review changed row_end.",
    )
    _require(
        getattr(reviewed_variable, "units_hint", None) == expected_variable.units_hint,
        "LLM variable-plausibility review changed units_hint.",
    )
    _require(
        getattr(reviewed_variable, "summary_style_hint", None) == expected_variable.summary_style_hint,
        "LLM variable-plausibility review changed summary_style_hint.",
    )
    reviewed_levels = getattr(reviewed_variable, "levels", [])
    _require(
        len(reviewed_levels) == len(expected_variable.levels),
        "LLM variable-plausibility review changed the number of attached levels.",
    )
    for expected_level, reviewed_level in zip(expected_variable.levels, reviewed_levels, strict=True):
        _validate_level_identity(reviewed_level, expected_level)


def _validate_level_identity(
    reviewed_level: object,
    expected_level: LLMVariablePlausibilityLevelPayload,
) -> None:
    """Require the reviewed level to preserve all prompt-supplied identity fields exactly."""
    _require(
        getattr(reviewed_level, "level_name", None) == expected_level.level_name,
        "LLM variable-plausibility review changed level_name.",
    )
    _require(
        getattr(reviewed_level, "level_label", None) == expected_level.level_label,
        "LLM variable-plausibility review changed level_label.",
    )
    _require(
        getattr(reviewed_level, "row_idx", None) == expected_level.row_idx,
        "LLM variable-plausibility review changed row_idx.",
    )


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
