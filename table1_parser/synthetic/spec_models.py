"""Pydantic models and helpers for synthetic Table 1 document specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class SyntheticLayoutOptions(BaseModel):
    """Visual layout switches for generated tables."""

    indent_levels: bool = True
    horizontal_rules: bool = True
    parent_rows_with_values: bool = False
    wrapped_labels: bool = False


class CategoricalLevelSpec(BaseModel):
    """One categorical level row."""

    label: str
    values: list[str] = Field(default_factory=list)


class ContinuousRowSpec(BaseModel):
    """A one-row continuous variable or scalar count row."""

    type: Literal["continuous"]
    label: str
    values: list[str] = Field(default_factory=list)


class CategoricalRowSpec(BaseModel):
    """A categorical parent row plus level rows."""

    type: Literal["categorical"]
    label: str
    levels: list[CategoricalLevelSpec] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)


class CategoricalInlineRowSpec(BaseModel):
    """A one-row inline categorical summary."""

    type: Literal["categorical_inline"]
    label: str
    values: list[str] = Field(default_factory=list)


class SectionHeaderRowSpec(BaseModel):
    """A display-only section header row."""

    type: Literal["section_header"]
    label: str


SyntheticRowSpec = Annotated[
    ContinuousRowSpec | CategoricalRowSpec | CategoricalInlineRowSpec | SectionHeaderRowSpec,
    Field(discriminator="type"),
]


class SyntheticDocumentSpec(BaseModel):
    """Full structured input for a synthetic document."""

    document_title: str
    subtitle: str | None = None
    paragraphs: list[str] = Field(default_factory=list)
    table_caption: str
    columns: list[str] = Field(min_length=1)
    rows: list[SyntheticRowSpec] = Field(default_factory=list)
    footnotes: list[str] = Field(default_factory=list)
    layout: SyntheticLayoutOptions = Field(default_factory=SyntheticLayoutOptions)


class SyntheticDisplayRow(BaseModel):
    """Flattened rendered row used across HTML, PDF, and truth generation."""

    body_row_idx: int = Field(ge=0)
    row_type: Literal["continuous", "categorical_parent", "level", "categorical_inline", "section_header"]
    label: str
    values: list[str] = Field(default_factory=list)
    variable_name: str | None = None
    variable_type: Literal["continuous", "categorical", "categorical_inline", "section_header"] | None = None
    level_label: str | None = None
    parent_label: str | None = None
    indent_level: int = Field(default=0, ge=0)


def load_table_spec(path: str | Path) -> SyntheticDocumentSpec:
    """Read and validate a synthetic document spec from JSON."""

    spec_path = Path(path)
    return SyntheticDocumentSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))


def slugify_label(value: str) -> str:
    """Create a stable identifier-like label."""

    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    collapsed = "_".join(part for part in cleaned.split("_") if part)
    return collapsed or "row"


def expand_display_rows(spec: SyntheticDocumentSpec) -> list[SyntheticDisplayRow]:
    """Flatten structured row definitions into display rows."""

    rows: list[SyntheticDisplayRow] = []
    next_row_idx = 0
    for row in spec.rows:
        if isinstance(row, ContinuousRowSpec):
            rows.append(
                SyntheticDisplayRow(
                    body_row_idx=next_row_idx,
                    row_type="continuous",
                    label=row.label,
                    values=row.values,
                    variable_name=slugify_label(row.label),
                    variable_type="continuous",
                )
            )
            next_row_idx += 1
            continue

        if isinstance(row, CategoricalInlineRowSpec):
            rows.append(
                SyntheticDisplayRow(
                    body_row_idx=next_row_idx,
                    row_type="categorical_inline",
                    label=row.label,
                    values=row.values,
                    variable_name=slugify_label(row.label),
                    variable_type="categorical_inline",
                )
            )
            next_row_idx += 1
            continue

        if isinstance(row, SectionHeaderRowSpec):
            rows.append(
                SyntheticDisplayRow(
                    body_row_idx=next_row_idx,
                    row_type="section_header",
                    label=row.label,
                    variable_name=slugify_label(row.label),
                    variable_type="section_header",
                )
            )
            next_row_idx += 1
            continue

        parent_values = row.values if spec.layout.parent_rows_with_values else []
        rows.append(
            SyntheticDisplayRow(
                body_row_idx=next_row_idx,
                row_type="categorical_parent",
                label=row.label,
                values=parent_values,
                variable_name=slugify_label(row.label),
                variable_type="categorical",
            )
        )
        next_row_idx += 1
        for level in row.levels:
            rows.append(
                SyntheticDisplayRow(
                    body_row_idx=next_row_idx,
                    row_type="level",
                    label=level.label,
                    values=level.values,
                    variable_name=slugify_label(row.label),
                    variable_type="categorical",
                    level_label=level.label,
                    parent_label=row.label,
                    indent_level=1 if spec.layout.indent_levels else 0,
                )
            )
            next_row_idx += 1

    return rows


def spec_to_json(spec: SyntheticDocumentSpec) -> str:
    """Serialize a validated spec for embedding in generated HTML."""

    return json.dumps(spec.model_dump(mode="json"), indent=2)
