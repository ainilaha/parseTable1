"""Detect likely semantic roles for table columns from normalized headers."""

from __future__ import annotations

from table1_parser.heuristics.models import ColumnRoleGuess
from table1_parser.normalize.cleaner import clean_text
from table1_parser.schemas import NormalizedTable


def detect_column_roles(table: NormalizedTable) -> list[ColumnRoleGuess]:
    """Detect likely roles for each normalized table column."""
    cleaned_rows = table.metadata.get("cleaned_rows", [])
    grid = cleaned_rows if isinstance(cleaned_rows, list) else []
    header_rows = [grid[row_idx] for row_idx in table.header_rows if row_idx < len(grid)]
    if not header_rows:
        return [
            ColumnRoleGuess(col_idx=col_idx, header_label="", role="unknown", confidence=0.0)
            for col_idx in range(table.n_cols)
        ]

    guesses: list[ColumnRoleGuess] = []
    for col_idx in range(table.n_cols):
        parts = [row[col_idx] for row in header_rows if col_idx < len(row) and row[col_idx]]
        label = clean_text(" ".join(parts))
        lowered = label.lower()
        if not label:
            role, confidence = "unknown", 0.4
        elif (
            "p-value" in lowered
            or "p value" in lowered
            or lowered.startswith("pvalue")
            or lowered == "p"
            or ("trend" in lowered and "p" in lowered)
        ):
            role, confidence = "p_value", 0.98
        elif "smd" in lowered:
            role, confidence = "smd", 0.98
        elif "overall" in lowered or lowered in {"all", "total"}:
            role, confidence = "overall", 0.95
        elif lowered in {"control", "controls"}:
            role, confidence = "comparison_group", 0.92
        elif lowered in {"case", "cases"}:
            role, confidence = "group", 0.92
        elif lowered.startswith("q") and len(lowered) <= 3:
            role, confidence = "group", 0.8
        elif "(" in lowered and "n=" in lowered:
            role, confidence = "group", 0.78
        else:
            role, confidence = "unknown", 0.45
        guesses.append(
            ColumnRoleGuess(
                col_idx=col_idx,
                header_label=label,
                role=role,
                confidence=confidence,
            )
        )
    return guesses
