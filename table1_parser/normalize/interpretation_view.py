"""Compact normalized-table view for later interpretation stages."""

from __future__ import annotations

from typing import Any

from table1_parser.schemas import NormalizedTable


def build_interpretation_view(table: NormalizedTable) -> dict[str, Any]:
    """Create a compact dictionary view suitable for later LLM prompting."""
    return {
        "table_id": table.table_id,
        "title": table.title,
        "caption": table.caption,
        "header_rows": table.header_rows,
        "body_rows": table.body_rows,
        "rows": [
            {
                "row_idx": row_view.row_idx,
                "first_cell_raw": row_view.first_cell_raw,
                "first_cell_normalized": row_view.first_cell_normalized,
                "first_cell_alpha_only": row_view.first_cell_alpha_only,
                "numeric_cell_count": row_view.numeric_cell_count,
                "nonempty_cell_count": row_view.nonempty_cell_count,
                "has_trailing_values": row_view.has_trailing_values,
            }
            for row_view in table.row_views
        ],
    }
