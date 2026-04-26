"""Schemas for TableDefinition variable-plausibility review prompts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from table1_parser.schemas.table_definition import DefinedVariableType


class _CompactPayloadModel(BaseModel):
    """Base model for compact prompt payload objects with short serialized keys."""

    model_config = ConfigDict(populate_by_name=True)


class LLMVariablePlausibilityLevelPayload(_CompactPayloadModel):
    """One level included as evidence for a variable-level plausibility judgment."""

    row_idx: int = Field(alias="i", ge=0)
    level_name: str
    level_label: str


class LLMVariablePlausibilityVariablePayload(_CompactPayloadModel):
    """One compact variable record supplied to the plausibility-review prompt."""

    variable_name: str
    variable_label: str
    variable_type: DefinedVariableType = Field(alias="type")
    row_start: int = Field(alias="r0", ge=0)
    row_end: int = Field(alias="r1", ge=0)
    levels: list[LLMVariablePlausibilityLevelPayload] = Field(default_factory=list)
    units_hint: str | None = Field(default=None, alias="units")
    summary_style_hint: str | None = Field(default=None, alias="style")


class LLMVariablePlausibilityInputPayload(_CompactPayloadModel):
    """Structured compact payload for one-table variable-plausibility review."""

    table_id: str = Field(alias="id")
    table_text: str | None = Field(default=None, alias="table")
    variables: list[LLMVariablePlausibilityVariablePayload] = Field(default_factory=list, alias="vars")


class LLMVariablePlausibilityLevelReview(BaseModel):
    """Reviewed level object echoed back with the parent variable assessment."""

    level_name: str
    level_label: str
    row_idx: int = Field(ge=0)


class LLMVariablePlausibilityVariableReview(BaseModel):
    """One reviewed variable together with a semantic plausibility score."""

    variable_name: str
    variable_label: str
    variable_type: DefinedVariableType = "unknown"
    row_start: int = Field(ge=0)
    row_end: int = Field(ge=0)
    levels: list[LLMVariablePlausibilityLevelReview] = Field(default_factory=list)
    units_hint: str | None = None
    summary_style_hint: str | None = None
    plausibility_score: float = Field(ge=0.0, le=1.0)
    plausibility_note: str | None = None


class LLMVariablePlausibilityTableReview(BaseModel):
    """Structured output for one-table variable-plausibility review."""

    table_id: str
    variables: list[LLMVariablePlausibilityVariableReview] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    overall_plausibility: float | None = Field(default=None, ge=0.0, le=1.0)
