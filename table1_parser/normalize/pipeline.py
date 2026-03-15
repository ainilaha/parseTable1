"""Pipeline helper for converting extracted tables into normalized tables."""

from __future__ import annotations

from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.header_detector import detect_header_rows
from table1_parser.normalize.row_signature import build_row_signature
from table1_parser.schemas import ExtractedTable, NormalizedTable


def _rows_from_extracted_table(table: ExtractedTable) -> list[list[str]]:
    """Rebuild the row-major grid from extracted cells while preserving order."""
    rows = [["" for _ in range(table.n_cols)] for _ in range(table.n_rows)]
    for cell in table.cells:
        if cell.row_idx < table.n_rows and cell.col_idx < table.n_cols:
            rows[cell.row_idx][cell.col_idx] = cell.text
    return rows


def normalize_extracted_table(table: ExtractedTable) -> NormalizedTable:
    """Convert a raw extracted table into the normalized intermediate schema."""
    raw_rows = _rows_from_extracted_table(table)
    cleaned_rows = [[clean_text(cell) for cell in row] for row in raw_rows]
    header_rows, body_rows = detect_header_rows(cleaned_rows)
    row_views = [build_row_signature(row_idx, raw_rows[row_idx]) for row_idx in body_rows]

    metadata = {
        **table.metadata,
        "source_page_num": table.page_num,
        "extraction_backend": table.extraction_backend,
        "cleaned_rows": cleaned_rows,
    }
    return NormalizedTable(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        header_rows=header_rows,
        body_rows=body_rows,
        row_views=row_views,
        n_rows=table.n_rows,
        n_cols=table.n_cols,
        metadata=metadata,
    )
