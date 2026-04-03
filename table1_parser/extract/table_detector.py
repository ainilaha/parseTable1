"""Heuristics for identifying likely table candidates in a PDF."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


TABLE_CAPTION_LINE_PATTERN = re.compile(r"^\s*table\s*(\d+)\b(?:\s*[:.])?", re.IGNORECASE)
NUMERIC_TOKEN_PATTERN = re.compile(r"\d")
ALPHA_TOKEN_PATTERN = re.compile(r"[A-Za-z]")


class DetectedTableCandidate(BaseModel):
    """A raw extracted table candidate with detection metadata and score."""

    page_num: int = Field(ge=1)
    table_index: int = Field(ge=0)
    bbox: tuple[float, float, float, float] | None = None
    raw_rows: list[list[str]] = Field(default_factory=list)
    caption: str | None = None
    page_text: str | None = None
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _normalize_rows(raw_rows: list[list[Any]]) -> list[list[str]]:
    """Normalize a raw table grid and pad rows into a rectangle."""
    if not raw_rows:
        return []
    max_cols = max((len(row) for row in raw_rows), default=0)
    return [[("" if cell is None else str(cell).strip()) for cell in row] + [""] * (max_cols - len(row)) for row in raw_rows]


def _is_rectangular(raw_rows: list[list[Any]]) -> bool:
    """Return whether all rows in the extracted grid have the same width."""
    row_lengths = {len(row) for row in raw_rows if row}
    return bool(row_lengths) and len(row_lengths) == 1


def _find_table_caption_lines(text_block: str) -> list[str]:
    """Return caption-like lines that begin with a table label."""
    captions: list[str] = []
    for raw_line in text_block.splitlines():
        line = raw_line.strip()
        if line and TABLE_CAPTION_LINE_PATTERN.match(line):
            captions.append(line)
    return captions


def _find_table_line(page_text: str) -> str | None:
    """Return the first caption-like table line from a text block."""
    caption_lines = _find_table_caption_lines(page_text)
    if not caption_lines:
        return None
    return caption_lines[0]


def _caption_for_index(
    explicit_caption: str | None,
    page_text: str,
    table_index: int,
    table_count: int | None = None,
) -> str | None:
    """Choose the best available caption for a candidate on a page."""
    if explicit_caption:
        return explicit_caption
    caption_lines = _find_table_caption_lines(page_text)
    if not caption_lines:
        return None
    caption_start_index = 0
    if table_count is not None and table_count > len(caption_lines):
        caption_start_index = table_count - len(caption_lines)
    if table_index < caption_start_index:
        return None
    caption_index = table_index - caption_start_index
    if 0 <= caption_index < len(caption_lines):
        return caption_lines[caption_index]
    return None


def _safe_extract_text(page: Any) -> str:
    """Extract page text while tolerating backend quirks."""
    try:
        return (page.extract_text() or "").strip()
    except Exception:
        return ""


def score_candidate(candidate: DetectedTableCandidate) -> DetectedTableCandidate:
    """Assign a table-likelihood score to an extracted table candidate."""
    if candidate.caption:
        effective_caption = candidate.caption
    elif candidate.raw_rows and candidate.raw_rows[0]:
        first_cell = candidate.raw_rows[0][0].strip()
        first_line = first_cell.splitlines()[0].strip() if first_cell else ""
        effective_caption = first_line if TABLE_CAPTION_LINE_PATTERN.match(first_line) else None
    else:
        effective_caption = None
    if not effective_caption:
        caption_table_number = None
    else:
        caption_line = _find_table_line(effective_caption)
        match = TABLE_CAPTION_LINE_PATTERN.match(caption_line) if caption_line else None
        caption_table_number = int(match.group(1)) if match is not None else None
    caption_match = caption_table_number is not None
    table_1_match = caption_table_number == 1
    first_column_values = [row[0] for row in candidate.raw_rows if row]
    populated_first_column = [value for value in first_column_values if value.strip()]
    first_column_text_ratio = (
        sum(bool(ALPHA_TOKEN_PATTERN.search(value)) for value in populated_first_column) / len(populated_first_column)
        if populated_first_column
        else 0.0
    )
    later_column_values = [cell for row in candidate.raw_rows for cell in row[1:]]
    populated_later_columns = [value for value in later_column_values if value.strip()]
    later_column_numeric_ratio = (
        sum(bool(NUMERIC_TOKEN_PATTERN.search(value)) for value in populated_later_columns) / len(populated_later_columns)
        if populated_later_columns
        else 0.0
    )
    rectangular = bool(candidate.metadata.get("is_rectangular", False))
    min_shape = len(candidate.raw_rows) >= 2 and max((len(row) for row in candidate.raw_rows), default=0) >= 2

    score = 0.4 * caption_match
    score += 0.05 if table_1_match else 0.0
    score += 0.25 if first_column_text_ratio >= 0.6 else 0.0
    score += 0.2 if later_column_numeric_ratio >= 0.5 else 0.0
    score += 0.1 if rectangular else 0.0
    score += 0.05 if min_shape else 0.0
    return candidate.model_copy(
        update={
            "caption": effective_caption,
            "score": min(score, 1.0),
            "metadata": {
                **candidate.metadata,
                "signals": {
                    "caption_match": caption_match,
                    "table_1_match": table_1_match,
                    "caption_table_number": caption_table_number,
                    "first_column_text_ratio": round(first_column_text_ratio, 4),
                    "later_column_numeric_ratio": round(later_column_numeric_ratio, 4),
                    "rectangular": rectangular,
                },
            },
        }
    )


def detect_page_candidates(page: Any, page_num: int) -> list[DetectedTableCandidate]:
    """Detect raw table candidates on a single page."""
    from table1_parser.extract.layout_fallback import build_text_layout_candidates, detect_horizontal_rules

    page_text = _safe_extract_text(page)
    try:
        raw_lines = getattr(page, "lines", []) or []
    except Exception:
        rule_segments = []
    else:
        rule_segments = [
            (
                float(line.get("x0", 0.0)),
                float(line.get("y0", 0.0)),
                float(line.get("x1", 0.0)),
                float(line.get("y1", line.get("y0", 0.0))),
            )
            for line in raw_lines
        ]
    if hasattr(page, "find_tables"):
        raw_tables_obj = page.find_tables()
        if raw_tables_obj is None:
            raw_tables = []
        else:
            tables_attr = getattr(raw_tables_obj, "tables", None)
            if tables_attr is not None:
                raw_tables = list(tables_attr)
            else:
                try:
                    raw_tables = list(raw_tables_obj)
                except TypeError:
                    raw_tables = []
    else:
        raw_tables = []
    candidates: list[DetectedTableCandidate] = []
    if raw_tables:
        table_count = len(raw_tables)
        for table_index, table in enumerate(raw_tables):
            raw_rows = table.extract() if hasattr(table, "extract") else table
            bbox = getattr(table, "bbox", None)
            if bbox is None or not hasattr(page, "crop"):
                nearby_caption = _find_table_line(page_text)
            else:
                top = bbox[1]
                crop_bbox = (0.0, max(0.0, top - 90.0), float(getattr(page, "width", bbox[2])), top)
                try:
                    cropped_page_text = _safe_extract_text(page.crop(crop_bbox))
                except Exception:
                    cropped_page_text = ""
                nearby_caption = _find_table_line(cropped_page_text)
            candidates.append(
                score_candidate(
                    DetectedTableCandidate(
                        page_num=page_num,
                        table_index=table_index,
                        bbox=bbox,
                        raw_rows=_normalize_rows(raw_rows),
                        caption=_caption_for_index(
                            nearby_caption,
                            page_text,
                            table_index,
                            table_count,
                        ),
                        page_text=page_text,
                        metadata={
                            "is_rectangular": _is_rectangular(raw_rows),
                            "horizontal_rules": detect_horizontal_rules(rule_segments, bbox),
                        },
                    )
                )
            )
        return candidates

    if hasattr(page, "extract_tables"):
        extracted_tables = page.extract_tables() or []
        table_count = len(extracted_tables)
        for table_index, raw_rows in enumerate(extracted_tables):
            candidates.append(
                score_candidate(
                    DetectedTableCandidate(
                        page_num=page_num,
                        table_index=table_index,
                        raw_rows=_normalize_rows(raw_rows),
                        caption=_caption_for_index(None, page_text, table_index, table_count),
                        page_text=page_text,
                        metadata={"is_rectangular": _is_rectangular(raw_rows)},
                    )
                )
            )
    if candidates:
        return candidates

    if not hasattr(page, "extract_words"):
        words = []
    else:
        try:
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
        except Exception:
            words = []
    try:
        chars = getattr(page, "chars", []) or []
    except Exception:
        chars = []
    return build_text_layout_candidates(
        page_num=page_num,
        page_text=page_text,
        words=words,
        chars=chars,
        rule_segments=rule_segments,
    )


def detect_table_candidates(pdf: Any) -> list[DetectedTableCandidate]:
    """Detect and score table candidates across the entire PDF."""
    candidates: list[DetectedTableCandidate] = []
    pages_attr = getattr(pdf, "pages", None)
    if pages_attr is not None and not callable(pages_attr):
        pages = list(pages_attr)
    else:
        page_count = getattr(pdf, "page_count", None)
        load_page = getattr(pdf, "load_page", None)
        if isinstance(page_count, int) and callable(load_page):
            pages = [load_page(index) for index in range(page_count)]
        elif callable(pages_attr):
            pages = list(pages_attr())
        else:
            raise TypeError("Unsupported PDF object: expected iterable pages or page_count/load_page().")
    for page_num, page in enumerate(pages, start=1):
        candidates.extend(detect_page_candidates(page, page_num))
    return candidates
