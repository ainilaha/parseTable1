"""Schemas for semantic LLM runtime monitoring artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LLMSemanticCallStatus = Literal[
    "skipped_disabled",
    "skipped_not_eligible",
    "skipped_configuration_error",
    "success",
    "provider_error",
    "validation_error",
]


class LLMSemanticCallRecord(BaseModel):
    """One monitored semantic-LLM call or skip decision for a table."""

    table_id: str
    table_index: int = Field(ge=0)
    table_family: str | None = None
    should_run_llm_semantics: bool
    status: LLMSemanticCallStatus
    started_at: str | None = None
    completed_at: str | None = None
    elapsed_seconds: float | None = Field(default=None, ge=0.0)
    trace_dir: str | None = None
    header_row_count: int = Field(default=0, ge=0)
    body_row_count: int = Field(default=0, ge=0)
    header_cell_count: int = Field(default=0, ge=0)
    body_cell_count: int = Field(default=0, ge=0)
    deterministic_variable_count: int = Field(default=0, ge=0)
    deterministic_column_count: int = Field(default=0, ge=0)
    retrieved_passage_count: int = Field(default=0, ge=0)
    retrieved_context_char_count: int = Field(default=0, ge=0)
    prompt_char_count: int | None = Field(default=None, ge=0)
    prompt_line_count: int | None = Field(default=None, ge=0)
    response_char_count: int | None = Field(default=None, ge=0)
    output_variable_count: int | None = Field(default=None, ge=0)
    output_column_count: int | None = Field(default=None, ge=0)
    error_message: str | None = None


class LLMSemanticMonitoringReport(BaseModel):
    """Paper-level summary of semantic-LLM activity during one parse run."""

    report_timestamp: str
    llm_disabled: bool = False
    provider: str | None = None
    model: str | None = None
    items: list[LLMSemanticCallRecord] = Field(default_factory=list)
