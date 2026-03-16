"""Pipeline helper for converting extracted tables into normalized tables."""

from __future__ import annotations

import re

from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.header_detector import detect_header_rows_with_metadata
from table1_parser.normalize.row_signature import build_row_signature
from table1_parser.schemas import ExtractedTable, NormalizedTable
from table1_parser.schemas.normalized_table import RowView


ALPHA_PATTERN = re.compile(r"[A-Za-z]")
ALNUM_PATTERN = re.compile(r"[A-Za-z0-9]")


def _rows_from_extracted_table(table: ExtractedTable) -> list[list[str]]:
    """Rebuild the row-major grid from extracted cells while preserving order."""
    rows = [["" for _ in range(table.n_cols)] for _ in range(table.n_rows)]
    for cell in table.cells:
        if cell.row_idx < table.n_rows and cell.col_idx < table.n_cols:
            rows[cell.row_idx][cell.col_idx] = cell.text
    return rows


def _is_noninformative_cell(value: str) -> bool:
    """Return whether a cell is empty or too weak to act as a reliable row label."""
    cleaned = clean_text(value)
    if not cleaned:
        return True
    if not ALNUM_PATTERN.search(cleaned):
        return True
    return len(cleaned) <= 2 and not ALPHA_PATTERN.search(cleaned)


def _looks_like_label_cell(value: str) -> bool:
    """Return whether a cell resembles a meaningful row-label cell."""
    cleaned = clean_text(value)
    return bool(cleaned) and bool(ALPHA_PATTERN.search(cleaned)) and len(cleaned) >= 2


def _should_drop_leading_column(rows: list[list[str]]) -> bool:
    """Return whether the leftmost column is mostly empty/noisy and the next column looks like labels."""
    if not rows or not rows[0] or len(rows[0]) < 2:
        return False
    first_column = [row[0] for row in rows]
    second_column = [row[1] for row in rows]
    first_noninformative = sum(_is_noninformative_cell(value) for value in first_column)
    first_meaningful = sum(_looks_like_label_cell(value) for value in first_column)
    second_label_like = sum(_looks_like_label_cell(value) for value in second_column)
    row_count = len(rows)
    return (
        first_noninformative / row_count >= 0.85
        and first_meaningful <= max(1, row_count // 10)
        and second_label_like >= max(3, row_count // 3)
    )


def _should_drop_trailing_column(rows: list[list[str]]) -> bool:
    """Return whether the rightmost column is mostly empty/noisy compared with the table body."""
    if not rows or not rows[0] or len(rows[0]) < 2:
        return False
    last_column = [row[-1] for row in rows]
    previous_column = [row[-2] for row in rows]
    last_noninformative = sum(_is_noninformative_cell(value) for value in last_column)
    previous_informative = sum(not _is_noninformative_cell(value) for value in previous_column)
    row_count = len(rows)
    return (
        last_noninformative / row_count >= 0.9
        and previous_informative >= max(2, row_count // 4)
    )


def _trim_edge_columns(rows: list[list[str]]) -> tuple[list[list[str]], int, int]:
    """Drop a spurious leading or trailing edge column using conservative table-level signals."""
    if not rows:
        return rows, 0, 0
    drop_leading = 1 if _should_drop_leading_column(rows) else 0
    rows_after_leading = [row[drop_leading:] for row in rows]
    drop_trailing = 1 if _should_drop_trailing_column(rows_after_leading) else 0
    if drop_trailing:
        trimmed_rows = [row[:-drop_trailing] for row in rows_after_leading]
    else:
        trimmed_rows = rows_after_leading
    return trimmed_rows, drop_leading, drop_trailing


def _first_column_bbox_by_row(
    table: ExtractedTable,
    first_col_idx: int,
) -> tuple[dict[int, tuple[float, float, float, float]], float | None]:
    """Collect first-column bounding boxes and a left-edge baseline when available."""
    bbox_by_row: dict[int, tuple[float, float, float, float]] = {}
    x0_values: list[float] = []
    for cell in table.cells:
        if cell.col_idx != first_col_idx or cell.bbox is None or cell.row_idx >= table.n_rows:
            continue
        bbox_by_row[cell.row_idx] = cell.bbox
        x0_values.append(cell.bbox[0])
    return bbox_by_row, (min(x0_values) if x0_values else None)


def _row_bounds_from_metadata(table: ExtractedTable) -> list[tuple[float, float]] | None:
    """Return per-row vertical bounds when extraction preserved them."""
    raw_bounds = table.metadata.get("row_bounds")
    if not isinstance(raw_bounds, list) or len(raw_bounds) != table.n_rows:
        return None
    bounds: list[tuple[float, float]] = []
    for item in raw_bounds:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return None
        bounds.append((float(item[0]), float(item[1])))
    return bounds


def _horizontal_rules_from_metadata(table: ExtractedTable) -> list[float] | None:
    """Return detected wide horizontal rule positions when available."""
    raw_rules = table.metadata.get("horizontal_rules")
    if not isinstance(raw_rules, list):
        return None
    return [float(value) for value in raw_rules]


def _indentation_is_informative(row_views: list[RowView]) -> bool:
    """Return whether body-row indentation shows meaningful hierarchy for this table."""
    indent_levels = [row_view.indent_level for row_view in row_views if row_view.indent_level is not None]
    if len(indent_levels) < 3:
        return False
    baseline = min(indent_levels)
    meaningful_offsets = [level - baseline for level in indent_levels if level - baseline >= 2]
    if len(meaningful_offsets) < 2:
        return False
    return len(set(indent_levels)) >= 2


def normalize_extracted_table(table: ExtractedTable) -> NormalizedTable:
    """Convert a raw extracted table into the normalized intermediate schema."""
    raw_rows = _rows_from_extracted_table(table)
    raw_rows, dropped_leading_cols, dropped_trailing_cols = _trim_edge_columns(raw_rows)
    cleaned_rows = [[clean_text(cell) for cell in row] for row in raw_rows]
    header_rows, body_rows, header_detection = detect_header_rows_with_metadata(
        cleaned_rows,
        row_bounds=_row_bounds_from_metadata(table),
        horizontal_rules=_horizontal_rules_from_metadata(table),
    )
    first_column_bboxes, base_x0 = _first_column_bbox_by_row(table, first_col_idx=dropped_leading_cols)
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
        "dropped_leading_cols": dropped_leading_cols,
        "dropped_trailing_cols": dropped_trailing_cols,
        "header_detection": header_detection,
        "indentation_informative": _indentation_is_informative(row_views),
    }
    return NormalizedTable(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        header_rows=header_rows,
        body_rows=body_rows,
        row_views=row_views,
        n_rows=table.n_rows,
        n_cols=len(raw_rows[0]) if raw_rows else 0,
        metadata=metadata,
    )
