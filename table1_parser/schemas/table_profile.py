"""Schemas for deterministic table-family routing."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TableFamily = Literal["descriptive_characteristics", "estimate_results", "unknown"]


class TableProfile(BaseModel):
    """A deterministic route decision for one normalized table."""

    table_id: str
    title: str | None = None
    caption: str | None = None
    table_family: TableFamily = "unknown"
    should_run_llm_semantics: bool
    family_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
