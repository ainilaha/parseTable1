"""Schemas for paper-level candidate variable inventory artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from table1_parser.schemas.document_context import SectionRoleHint


VariableMentionSourceType = Literal[
    "text_based",
    "table_variable_label",
    "table_variable_name",
    "table_title",
    "table_caption",
    "table_grouping_label",
]

VariableInterpretationStatus = Literal["uninterpreted", "merged_conservatively", "needs_review"]


class VariableMention(BaseModel):
    """One raw mention supporting a paper-level candidate variable."""

    mention_id: str
    raw_label: str
    normalized_label: str
    source_type: VariableMentionSourceType
    section_id: str | None = None
    heading: str | None = None
    role_hint: SectionRoleHint | None = None
    paragraph_index: int | None = Field(default=None, ge=0)
    evidence_text: str | None = None
    table_id: str | None = None
    table_index: int | None = Field(default=None, ge=0)
    table_label: str | None = None
    priority_weight: float = Field(default=0.0, ge=0.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class VariableCandidate(BaseModel):
    """One merged paper-level candidate variable."""

    candidate_id: str
    preferred_label: str
    normalized_label: str
    alternate_labels: list[str] = Field(default_factory=list)
    supporting_mention_ids: list[str] = Field(default_factory=list)
    source_types: list[VariableMentionSourceType] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    section_role_hints: list[SectionRoleHint] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    table_indices: list[int] = Field(default_factory=list)
    text_support_count: int = Field(default=0, ge=0)
    table_support_count: int = Field(default=0, ge=0)
    caption_support_count: int = Field(default=0, ge=0)
    priority_score: float = Field(default=0.0, ge=0.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    interpretation_status: VariableInterpretationStatus = "uninterpreted"
    notes: list[str] = Field(default_factory=list)


class PaperVariableInventory(BaseModel):
    """Paper-level candidate variable inventory."""

    paper_id: str
    mentions: list[VariableMention] = Field(default_factory=list)
    candidates: list[VariableCandidate] = Field(default_factory=list)
