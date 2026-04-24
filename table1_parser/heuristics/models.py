"""Small helper models for deterministic heuristic interpretation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RowClass = Literal[
    "variable_header",
    "level_row",
    "binary_variable_row",
    "continuous_variable_row",
    "section_header",
    "unknown",
]
ColumnRoleGuessType = Literal[
    "overall",
    "group",
    "comparison_group",
    "p_value",
    "smd",
    "unknown",
]
ValuePatternType = Literal[
    "count_pct",
    "mean_sd",
    "median_iqr",
    "p_value",
    "n_only",
    "unknown",
]
VariableKind = Literal["continuous", "categorical", "binary", "unknown"]


class RowClassification(BaseModel):
    """A conservative structural label for a normalized body row."""

    row_idx: int = Field(ge=0)
    classification: RowClass
    confidence: float = Field(ge=0.0, le=1.0)


class VariableBlock(BaseModel):
    """A grouped candidate variable spanning one or more normalized rows."""

    variable_row_idx: int = Field(ge=0)
    row_start: int = Field(ge=0)
    row_end: int = Field(ge=0)
    variable_label: str
    variable_kind: VariableKind
    level_row_indices: list[int] = Field(default_factory=list)


class ColumnRoleGuess(BaseModel):
    """A guessed semantic role for a table column."""

    col_idx: int = Field(ge=0)
    header_label: str
    role: ColumnRoleGuessType
    confidence: float = Field(ge=0.0, le=1.0)


class ValuePatternGuess(BaseModel):
    """A guessed value pattern for a raw table cell string."""

    raw_value: str
    pattern: ValuePatternType
    confidence: float = Field(ge=0.0, le=1.0)
