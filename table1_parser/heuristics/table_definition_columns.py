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
    grouping_label = None
    for text in (table.title, table.caption):
        cleaned = clean_text(text or "")
        match = BY_PATTERN.search(cleaned)
        if match is not None:
            grouping_label = clean_text(match.group(1).strip(" :"))
            break
    grouping_name = normalize_label_text(grouping_label) if grouping_label else None
    columns: list[DefinedColumn] = []
    for guess in detect_column_roles(table):
        lowered = clean_text(guess.header_label).lower()
        if guess.col_idx == 0 and (not lowered or lowered in LABEL_COLUMN_TOKENS):
            continue
        role = guess.role if guess.role != "unknown" or not (grouping_name and clean_text(guess.header_label)) else "group"
        columns.append(
            DefinedColumn(
                col_idx=guess.col_idx,
                column_name=normalize_label_text(guess.header_label) or f"column_{guess.col_idx}",
                column_label=guess.header_label,
                inferred_role=role,
                grouping_variable_hint=grouping_name if role in {"overall", "group", "comparison_group"} else None,
                confidence=(
                    guess.confidence
                    if guess.role != "unknown" or not (grouping_name and clean_text(guess.header_label))
                    else max(guess.confidence, 0.72)
                ),
            )
        )
    if not columns:
        definition_confidence = None
    else:
        base = sum(column.confidence or 0.0 for column in columns) / len(columns)
        definition_confidence = min(1.0, round(base + 0.05, 4)) if grouping_name else round(base, 4)
    return ColumnDefinition(
        grouping_label=grouping_label,
        grouping_name=grouping_name,
        columns=columns,
        confidence=definition_confidence,
    )
