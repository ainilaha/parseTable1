"""Row signature generation for normalized tables."""

from __future__ import annotations

import re

from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.text_normalizer import alpha_only_text, normalize_label_text
from table1_parser.schemas import RowView


NUMERIC_PATTERN = re.compile(r"\d")
LEADING_SPACE_PATTERN = re.compile(r"^(\s+)")


def infer_indent_level(first_cell_raw: str) -> int | None:
    """Infer indent level from leading whitespace when preserved by extraction."""
    match = LEADING_SPACE_PATTERN.match(first_cell_raw)
    if not match:
        return None
    return len(match.group(1))


def build_row_signature(row_idx: int, raw_cells: list[str]) -> RowView:
    """Build a normalized row signature from raw cell content."""
    cleaned_cells = [clean_text(cell) for cell in raw_cells]
    first_cell_raw = raw_cells[0] if raw_cells else ""
    trailing_cells = cleaned_cells[1:] if len(cleaned_cells) > 1 else []
    nonempty_cell_count = sum(1 for cell in cleaned_cells if cell)
    numeric_cell_count = sum(1 for cell in cleaned_cells if NUMERIC_PATTERN.search(cell))
    has_trailing_values = any(cell for cell in trailing_cells)

    return RowView(
        row_idx=row_idx,
        raw_cells=cleaned_cells,
        first_cell_raw=first_cell_raw,
        first_cell_normalized=normalize_label_text(first_cell_raw),
        first_cell_alpha_only=alpha_only_text(first_cell_raw),
        nonempty_cell_count=nonempty_cell_count,
        numeric_cell_count=numeric_cell_count,
        has_trailing_values=has_trailing_values,
        indent_level=infer_indent_level(first_cell_raw),
        likely_role=None,
    )
