"""Schemas for raw table extraction outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TableCell(BaseModel):
    """A single raw cell extracted from a table grid."""

    row_idx: int = Field(ge=0)
    col_idx: int = Field(ge=0)
    text: str
    page_num: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None
    extractor_name: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ExtractedTable(BaseModel):
    """Canonical representation of a table immediately after extraction."""

    table_id: str
    source_pdf: str
    page_num: int = Field(ge=1)
    title: str | None = None
    caption: str | None = None
    n_rows: int = Field(ge=0)
    n_cols: int = Field(ge=0)
    cells: list[TableCell] = Field(default_factory=list)
    extraction_backend: str
    metadata: dict[str, Any] = Field(default_factory=dict)
