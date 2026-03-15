"""Structured contracts reserved for future LLM-assisted interpretation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from table1_parser.schemas.normalized_table import RowView


class LLMTableContext(BaseModel):
    """Serialized normalized-table context passed to a future LLM layer."""

    table_id: str
    title: str | None = None
    caption: str | None = None
    row_views: list[RowView] = Field(default_factory=list)


class LLMTableParseResponse(BaseModel):
    """Placeholder structured response contract for future LLM output validation."""

    table_id: str
    referenced_row_indices: list[int] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
