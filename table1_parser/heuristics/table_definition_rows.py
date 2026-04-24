"""Deterministic row-variable assembly for TableDefinition."""

from __future__ import annotations

import re

from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.heuristics.variable_grouper import group_variable_blocks
from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import DefinedLevel, DefinedVariable, NormalizedTable
from table1_parser.text_cleaning import clean_text


SUMMARY_SUFFIX_PATTERN = re.compile(
    r"(?:,\s*)?(?:n\s*\(%\)|no\.\s*\(%\)|mean\s*[±+-]?\s*\(?sd\)?|median\s*\(?iqr\)?|mean\s*\(\s*sd\s*\))$",
    re.IGNORECASE,
)
PAREN_UNITS_PATTERN = re.compile(r"\(([^()]+)\)")
KNOWN_BINARY_LEVELS = {
    frozenset({"male", "female"}),
    frozenset({"yes", "no"}),
    frozenset({"case", "control"}),
    frozenset({"present", "absent"}),
    frozenset({"positive", "negative"}),
}


def build_defined_variables(table: NormalizedTable) -> list[DefinedVariable]:
    """Build value-free variable definitions from a normalized table."""
    row_views_by_idx = {row_view.row_idx: row_view for row_view in table.row_views}
    variables: list[DefinedVariable] = []
    for block in group_variable_blocks(table):
        parent_row = row_views_by_idx[block.variable_row_idx]
        levels = [
            DefinedLevel(
                level_name=clean_text(row_views_by_idx[row_idx].first_cell_raw),
                level_label=row_views_by_idx[row_idx].first_cell_raw,
                row_idx=row_idx,
                confidence=0.92,
            )
            for row_idx in block.level_row_indices
        ]
        if block.variable_kind == "continuous":
            variable_type = "continuous"
        elif block.variable_kind == "binary":
            variable_type = "binary"
        elif levels:
            level_names = {
                normalize_label_text(level.level_name).lower()
                for level in levels
                if normalize_label_text(level.level_name)
            }
            variable_type = "binary" if frozenset(level_names) in KNOWN_BINARY_LEVELS else "categorical"
        else:
            variable_type = "unknown"
        cleaned = clean_text(parent_row.first_cell_raw)
        without_suffix = SUMMARY_SUFFIX_PATTERN.sub("", cleaned).strip(" ,")
        without_paren_units = PAREN_UNITS_PATTERN.sub("", without_suffix).strip(" ,")
        variable_name = normalize_label_text(without_paren_units) or normalize_label_text(cleaned)
        units_hint = None
        if "," in cleaned:
            suffix = clean_text(cleaned.rsplit(",", maxsplit=1)[-1])
            if suffix and "n (%)" not in suffix.lower() and len(suffix) <= 20:
                units_hint = suffix
        if units_hint is None:
            match = PAREN_UNITS_PATTERN.search(cleaned)
            if match is not None:
                candidate = clean_text(match.group(1))
                if candidate and candidate.lower() not in {"sd", "iqr", "%"} and len(candidate) <= 20:
                    units_hint = candidate
        label = clean_text(parent_row.raw_cells[0]).lower() if parent_row.raw_cells else ""
        if "n (%)" in label or "no. (%)" in label:
            summary_style_hint = "count_pct"
        else:
            summary_style_hint = None
            for cell in [cell for cell in parent_row.raw_cells[1:] if clean_text(cell)]:
                pattern = detect_value_pattern(cell).pattern
                if pattern != "unknown":
                    summary_style_hint = pattern
                    break
            if summary_style_hint is None and levels:
                summary_style_hint = "count_pct"
        confidence = 0.55
        if variable_type == "continuous":
            confidence = 0.9
        elif variable_type == "binary":
            confidence = 0.95
        elif variable_type == "categorical":
            confidence = 0.92 if levels else 0.75
        variables.append(
            DefinedVariable(
                variable_name=variable_name,
                variable_label=parent_row.first_cell_raw,
                variable_type=variable_type,
                row_start=block.row_start,
                row_end=block.row_end,
                levels=levels,
                units_hint=units_hint,
                summary_style_hint=summary_style_hint,
                confidence=confidence,
            )
        )
    return variables
