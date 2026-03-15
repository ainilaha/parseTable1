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


def _first_column_bbox_by_row(table: ExtractedTable) -> tuple[dict[int, tuple[float, float, float, float]], float | None]:
    """Collect first-column bounding boxes and a left-edge baseline when available."""
    bbox_by_row: dict[int, tuple[float, float, float, float]] = {}
    x0_values: list[float] = []
    for cell in table.cells:
        if cell.col_idx != 0 or cell.bbox is None or cell.row_idx >= table.n_rows:
            continue
        bbox_by_row[cell.row_idx] = cell.bbox
        x0_values.append(cell.bbox[0])
    return bbox_by_row, (min(x0_values) if x0_values else None)


def normalize_extracted_table(table: ExtractedTable) -> NormalizedTable:
    """Convert a raw extracted table into the normalized intermediate schema."""
    raw_rows = _rows_from_extracted_table(table)
    cleaned_rows = [[clean_text(cell) for cell in row] for row in raw_rows]
    header_rows, body_rows = detect_header_rows(cleaned_rows)
    first_column_bboxes, base_x0 = _first_column_bbox_by_row(table)
    row_views = [
        build_row_signature(
            row_idx,
            raw_rows[row_idx],
            first_cell_bbox=first_column_bboxes.get(row_idx),
            base_x0=base_x0,
        )
        for row_idx in body_rows
    ]

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
