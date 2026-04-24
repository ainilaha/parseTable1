"""Schemas for table-level rescue and failure tracking."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ProcessingStage = Literal["extraction", "normalization", "table_definition", "parsed_table"]
ProcessingStatusValue = Literal["ok", "rescued", "failed"]


class TableProcessingAttempt(BaseModel):
    """One rescue, repair, or primary-path attempt recorded for a table."""

    stage: ProcessingStage
    name: str
    considered: bool = False
    ran: bool = False
    succeeded: bool = False
    note: str | None = None


class TableProcessingStatus(BaseModel):
    """Per-table parse status with rescue attempts and terminal failure details."""

    table_id: str
    status: ProcessingStatusValue = "ok"
    failure_stage: ProcessingStage | None = None
    failure_reason: str | None = None
    attempts: list[TableProcessingAttempt] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
