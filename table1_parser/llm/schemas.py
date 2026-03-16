"""Typed intermediate schemas for LLM-assisted interpretation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from table1_parser.schemas.parsed_table import ColumnRole, VariableType


class LLMLevelInterpretation(BaseModel):
    """LLM interpretation of a categorical level row."""

    label: str
    row_idx: int = Field(ge=0)


class LLMVariableInterpretation(BaseModel):
    """LLM interpretation of a candidate variable block."""

    variable_name: str
    variable_type: VariableType = "unknown"
    row_start: int = Field(ge=0)
    row_end: int = Field(ge=0)
    levels: list[LLMLevelInterpretation] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class LLMColumnInterpretation(BaseModel):
    """LLM interpretation of a semantic table column."""

    col_idx: int = Field(ge=0)
    column_name: str
    inferred_role: ColumnRole = "unknown"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class LLMTableInterpretation(BaseModel):
    """Typed LLM interpretation returned before final validation."""

    table_id: str
    variables: list[LLMVariableInterpretation] = Field(default_factory=list)
    columns: list[LLMColumnInterpretation] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LLMHeuristicPayload(BaseModel):
    """Compact heuristic context passed into prompt construction."""

    row_classifications: list[dict[str, object]] = Field(default_factory=list)
    variable_blocks: list[dict[str, object]] = Field(default_factory=list)
    column_roles: list[dict[str, object]] = Field(default_factory=list)


class LLMInputPayload(BaseModel):
    """Compact structured payload provided to the LLM."""

    table_id: str
    title: str | None = None
    caption: str | None = None
    header_rows: list[list[str]] = Field(default_factory=list)
    body_rows: list[list[str]] = Field(default_factory=list)
    heuristics: LLMHeuristicPayload = Field(default_factory=LLMHeuristicPayload)
