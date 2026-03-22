"""Deterministic column-definition assembly for TableDefinition."""

from __future__ import annotations

import re

from table1_parser.heuristics.column_role_detector import detect_column_roles
from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import ColumnDefinition, DefinedColumn, NormalizedTable


BY_PATTERN = re.compile(r"\b(?:stratified\s+)?by\s+(.+?)(?:[.;]|$)", re.IGNORECASE)
LABEL_COLUMN_TOKENS = {"characteristic", "characteristics", "variable", "variables", "factor", "covariate"}


def build_column_definition(table: NormalizedTable) -> ColumnDefinition:
    """Build value-free column definitions from a normalized table."""
    grouping_label = _grouping_label(table.title, table.caption)
    grouping_name = normalize_label_text(grouping_label) if grouping_label else None
    columns: list[DefinedColumn] = []
    for guess in detect_column_roles(table):
        if _skip_column(guess.col_idx, guess.header_label):
            continue
        role = _column_role(guess.role, guess.header_label, grouping_name)
        columns.append(
            DefinedColumn(
                col_idx=guess.col_idx,
                column_name=normalize_label_text(guess.header_label) or f"column_{guess.col_idx}",
                column_label=guess.header_label,
                inferred_role=role,
                grouping_variable_hint=grouping_name if role in {"overall", "group", "comparison_group"} else None,
                confidence=_column_confidence(guess.role, guess.header_label, guess.confidence, grouping_name),
            )
        )
    return ColumnDefinition(
        grouping_label=grouping_label,
        grouping_name=grouping_name,
        columns=columns,
        confidence=_column_definition_confidence(grouping_name, columns),
    )


def _grouping_label(title: str | None, caption: str | None) -> str | None:
    """Extract a grouping hint from title or caption text."""
    for text in (title, caption):
        cleaned = clean_text(text or "")
        match = BY_PATTERN.search(cleaned)
        if match is None:
            continue
        return clean_text(match.group(1).strip(" :"))
    return None


def _skip_column(col_idx: int, header_label: str) -> bool:
    """Return whether a detected column is only the row-label axis."""
    if col_idx != 0:
        return False
    lowered = clean_text(header_label).lower()
    return not lowered or lowered in LABEL_COLUMN_TOKENS


def _column_definition_confidence(grouping_name: str | None, columns: list[DefinedColumn]) -> float | None:
    """Return a simple confidence score for the column definition."""
    if not columns:
        return None
    base = sum(column.confidence or 0.0 for column in columns) / len(columns)
    if grouping_name:
        return min(1.0, round(base + 0.05, 4))
    return round(base, 4)


def _column_role(role: str, header_label: str, grouping_name: str | None) -> str:
    """Promote unlabeled data columns to groups when the table has a grouping hint."""
    if role != "unknown":
        return role
    if grouping_name and clean_text(header_label):
        return "group"
    return role


def _column_confidence(role: str, header_label: str, confidence: float, grouping_name: str | None) -> float:
    """Raise confidence slightly when an explicit grouping hint explains an unknown column."""
    if role != "unknown":
        return confidence
    if grouping_name and clean_text(header_label):
        return max(confidence, 0.72)
    return confidence
