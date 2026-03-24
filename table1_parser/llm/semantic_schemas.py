"""Schemas for LLM semantic TableDefinition interpretation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from table1_parser.schemas import TableContext, TableDefinition
from table1_parser.schemas.table_definition import DefinedColumnRole, DefinedVariableType


class LLMIndexedRowPayload(BaseModel):
    """One indexed table row supplied to the semantic LLM."""

    row_idx: int = Field(ge=0)
    cells: list[str] = Field(default_factory=list)


class LLMSemanticInputPayload(BaseModel):
    """Structured payload for LLM semantic TableDefinition interpretation."""

    table_id: str
    title: str | None = None
    caption: str | None = None
    header_rows: list[LLMIndexedRowPayload] = Field(default_factory=list)
    body_rows: list[LLMIndexedRowPayload] = Field(default_factory=list)
    deterministic_table_definition: TableDefinition
    retrieved_context: TableContext


class LLMSemanticLevelInterpretation(BaseModel):
    """LLM semantic interpretation of one categorical level row."""

    level_name: str
    level_label: str
    row_idx: int = Field(ge=0)
    evidence_passage_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    disagrees_with_deterministic: bool = False


class LLMSemanticVariableInterpretation(BaseModel):
    """LLM semantic interpretation of one row variable."""

    variable_name: str
    variable_label: str
    variable_type: DefinedVariableType = "unknown"
    row_start: int = Field(ge=0)
    row_end: int = Field(ge=0)
    levels: list[LLMSemanticLevelInterpretation] = Field(default_factory=list)
    evidence_passage_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    disagrees_with_deterministic: bool = False


class LLMSemanticColumnInterpretation(BaseModel):
    """LLM semantic interpretation of one table column."""

    col_idx: int = Field(ge=0)
    column_name: str
    column_label: str
    inferred_role: DefinedColumnRole = "unknown"
    grouping_variable_hint: str | None = None
    evidence_passage_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    disagrees_with_deterministic: bool = False


class LLMSemanticColumnDefinition(BaseModel):
    """LLM semantic interpretation of the table columns as a whole."""

    grouping_label: str | None = None
    grouping_name: str | None = None
    columns: list[LLMSemanticColumnInterpretation] = Field(default_factory=list)
    evidence_passage_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    disagrees_with_deterministic: bool = False


class LLMSemanticTableDefinition(BaseModel):
    """Value-free LLM semantic interpretation linked to deterministic table structure."""

    table_id: str
    variables: list[LLMSemanticVariableInterpretation] = Field(default_factory=list)
    column_definition: LLMSemanticColumnDefinition
    notes: list[str] = Field(default_factory=list)
    overall_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
