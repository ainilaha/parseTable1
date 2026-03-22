"""Deterministic row-variable assembly for TableDefinition."""

from __future__ import annotations

import re

from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.heuristics.variable_grouper import group_variable_blocks
from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import DefinedLevel, DefinedVariable, NormalizedTable


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
                level_name=_variable_name(row_views_by_idx[row_idx].first_cell_raw),
                level_label=row_views_by_idx[row_idx].first_cell_raw,
                row_idx=row_idx,
                confidence=0.92,
            )
            for row_idx in block.level_row_indices
        ]
        variable_type = _variable_type(block.variable_kind, levels)
        variables.append(
            DefinedVariable(
                variable_name=_variable_name(parent_row.first_cell_raw),
                variable_label=parent_row.first_cell_raw,
                variable_type=variable_type,
                row_start=block.row_start,
                row_end=block.row_end,
                levels=levels,
                units_hint=_units_hint(parent_row.first_cell_raw),
                summary_style_hint=_summary_style_hint(parent_row.raw_cells, levels),
                confidence=_variable_confidence(variable_type, levels),
            )
        )
    return variables


def _variable_name(label: str) -> str:
    """Return a matching-friendly variable or level name."""
    cleaned = clean_text(label)
    without_suffix = SUMMARY_SUFFIX_PATTERN.sub("", cleaned).strip(" ,")
    without_paren_units = PAREN_UNITS_PATTERN.sub("", without_suffix).strip(" ,")
    normalized = normalize_label_text(without_paren_units)
    if normalized:
        return normalized
    return normalize_label_text(cleaned)


def _units_hint(label: str) -> str | None:
    """Extract a short units hint from a label when visible."""
    cleaned = clean_text(label)
    if "," in cleaned:
        suffix = clean_text(cleaned.rsplit(",", maxsplit=1)[-1])
        if suffix and "n (%)" not in suffix.lower() and len(suffix) <= 20:
            return suffix
    match = PAREN_UNITS_PATTERN.search(cleaned)
    if match is None:
        return None
    candidate = clean_text(match.group(1))
    if not candidate or candidate.lower() in {"sd", "iqr", "%"}:
        return None
    if len(candidate) > 20:
        return None
    return candidate


def _summary_style_hint(raw_cells: list[str], levels: list[DefinedLevel]) -> str | None:
    """Infer a conservative summary style hint from visible text."""
    label = clean_text(raw_cells[0]).lower() if raw_cells else ""
    if "n (%)" in label or "no. (%)" in label:
        return "count_pct"
    trailing_cells = [cell for cell in raw_cells[1:] if clean_text(cell)]
    for cell in trailing_cells:
        pattern = detect_value_pattern(cell).pattern
        if pattern != "unknown":
            return pattern
    if levels:
        return "count_pct"
    return None


def _variable_type(variable_kind: str, levels: list[DefinedLevel]) -> str:
    """Map grouped row structure onto a variable type."""
    if variable_kind == "continuous":
        return "continuous"
    if levels:
        level_names = {level.level_name.lower() for level in levels}
        if frozenset(level_names) in KNOWN_BINARY_LEVELS:
            return "binary"
        return "categorical"
    return "unknown"


def _variable_confidence(variable_type: str, levels: list[DefinedLevel]) -> float:
    """Return a simple confidence score for a defined variable."""
    if variable_type == "continuous":
        return 0.9
    if variable_type == "binary":
        return 0.95
    if variable_type == "categorical":
        return 0.92 if levels else 0.75
    return 0.55
