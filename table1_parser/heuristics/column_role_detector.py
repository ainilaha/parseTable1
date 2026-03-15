"""Detect likely semantic roles for table columns from normalized headers."""

from __future__ import annotations

from table1_parser.heuristics.models import ColumnRoleGuess
from table1_parser.normalize.cleaner import clean_text
from table1_parser.schemas import NormalizedTable


def _header_grid(table: NormalizedTable) -> list[list[str]]:
    """Return cleaned row-major content preserved during normalization."""
    cleaned_rows = table.metadata.get("cleaned_rows", [])
    if isinstance(cleaned_rows, list):
        return cleaned_rows
    return []


def _column_label(header_rows: list[list[str]], col_idx: int) -> str:
    """Join non-empty header cells for a column into a single label."""
    parts = [row[col_idx] for row in header_rows if col_idx < len(row) and row[col_idx]]
    return clean_text(" ".join(parts))


def _detect_role(label: str) -> tuple[str, float]:
    """Map a column label to a conservative semantic role."""
    lowered = label.lower()
    if not label:
        return "unknown", 0.4
    if "p-value" in lowered or "p value" in lowered or lowered.startswith("pvalue") or lowered == "p":
        return "p_value", 0.98
    if "smd" in lowered:
        return "smd", 0.98
    if "overall" in lowered or lowered == "all":
        return "overall", 0.95
    if lowered in {"control", "controls"}:
        return "comparison_group", 0.92
    if lowered in {"case", "cases"}:
        return "group", 0.92
    if lowered.startswith("q") and len(lowered) <= 3:
        return "group", 0.8
    if "(" in lowered and "n=" in lowered:
        return "group", 0.78
    return "unknown", 0.45


def detect_column_roles(table: NormalizedTable) -> list[ColumnRoleGuess]:
    """Detect likely roles for each normalized table column."""
    grid = _header_grid(table)
    header_rows = [grid[row_idx] for row_idx in table.header_rows if row_idx < len(grid)]
    if not header_rows:
        return [
            ColumnRoleGuess(col_idx=col_idx, header_label="", role="unknown", confidence=0.0)
            for col_idx in range(table.n_cols)
        ]

    return [
        ColumnRoleGuess(
            col_idx=col_idx,
            header_label=label,
            role=role,
            confidence=confidence,
        )
        for col_idx in range(table.n_cols)
        for label, (role, confidence) in [(_column_label(header_rows, col_idx), _detect_role(_column_label(header_rows, col_idx)))]
    ]
