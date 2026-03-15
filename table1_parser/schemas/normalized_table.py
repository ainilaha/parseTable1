"""Schemas for normalized table structure."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RowRole = Literal[
    "header",
    "variable",
    "level",
    "statistic",
    "note",
    "unknown",
]


class RowView(BaseModel):
    """Normalized row-level features used by later parsing stages."""

    row_idx: int = Field(ge=0)
    raw_cells: list[str] = Field(default_factory=list)
    first_cell_raw: str
    first_cell_normalized: str
    first_cell_alpha_only: str
    nonempty_cell_count: int = Field(ge=0)
    numeric_cell_count: int = Field(ge=0)
    has_trailing_values: bool
    indent_level: int | None = Field(default=None, ge=0)
    likely_role: RowRole | None = None


class NormalizedTable(BaseModel):
    """Canonical representation of a table after normalization."""

    table_id: str
    title: str | None = None
    caption: str | None = None
    header_rows: list[int] = Field(default_factory=list)
    body_rows: list[int] = Field(default_factory=list)
    row_views: list[RowView] = Field(default_factory=list)
    n_rows: int = Field(ge=0)
    n_cols: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
