"""Schemas for variable-plausibility LLM runtime monitoring artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LLMVariablePlausibilityCallStatus = Literal[
    "skipped_not_eligible",
    "skipped_configuration_error",
    "success",
    "provider_error",
    "validation_error",
]


class LLMVariablePlausibilityCallRecord(BaseModel):
    """One monitored variable-plausibility review call or skip decision for a table."""

    table_id: str
    table_index: int = Field(ge=0)
    table_family: str | None = None
    eligible_for_review: bool
    status: LLMVariablePlausibilityCallStatus
    started_at: str | None = None
    completed_at: str | None = None
    elapsed_seconds: float | None = Field(default=None, ge=0.0)
    trace_dir: str | None = None
    deterministic_variable_count: int = Field(default=0, ge=0)
    continuous_variable_count: int = Field(default=0, ge=0)
    categorical_variable_count: int = Field(default=0, ge=0)
    binary_variable_count: int = Field(default=0, ge=0)
    attached_level_count: int = Field(default=0, ge=0)
    prompt_char_count: int | None = Field(default=None, ge=0)
    prompt_line_count: int | None = Field(default=None, ge=0)
    response_char_count: int | None = Field(default=None, ge=0)
    output_variable_count: int | None = Field(default=None, ge=0)
    error_message: str | None = None


class LLMVariablePlausibilityMonitoringReport(BaseModel):
    """Paper-level summary of variable-plausibility LLM activity during one review run."""

    report_timestamp: str
    provider: str | None = None
    model: str | None = None
    items: list[LLMVariablePlausibilityCallRecord] = Field(default_factory=list)
