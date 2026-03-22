"""Heuristics for identifying likely Table 1 candidates in a PDF."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


TABLE_1_PATTERN = re.compile(r"\btable\s*1\b", re.IGNORECASE)
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


def _normalize_cell(value: Any) -> str:
    """Normalize a raw table cell into stripped text."""
    return "" if value is None else str(value).strip()


def _normalize_rows(raw_rows: list[list[Any]]) -> list[list[str]]:
    """Normalize a raw table grid and pad rows into a rectangle."""
    if not raw_rows:
        return []
    max_cols = max((len(row) for row in raw_rows), default=0)
    return [[_normalize_cell(cell) for cell in row] + [""] * (max_cols - len(row)) for row in raw_rows]


def _is_rectangular(raw_rows: list[list[Any]]) -> bool:
    """Return whether all rows in the extracted grid have the same width."""
    row_lengths = {len(row) for row in raw_rows if row}
    return bool(row_lengths) and len(row_lengths) == 1


def _text_ratio(values: list[str]) -> float:
    """Measure how many populated cells contain alphabetic content."""
    populated = [value for value in values if value.strip()]
    if not populated:
        return 0.0
    return sum(bool(ALPHA_TOKEN_PATTERN.search(value)) for value in populated) / len(populated)


def _numeric_ratio(values: list[str]) -> float:
    """Measure how many populated cells contain numeric content."""
    populated = [value for value in values if value.strip()]
    if not populated:
        return 0.0
    return sum(bool(NUMERIC_TOKEN_PATTERN.search(value)) for value in populated) / len(populated)


def _flatten_later_columns(raw_rows: list[list[str]]) -> list[str]:
    """Collect non-first-column cells across the table."""
    return [cell for row in raw_rows for cell in row[1:]]


def _find_table_line(page_text: str) -> str | None:
    """Return the most relevant table caption line from page text."""
    for line in page_text.splitlines():
        if "table" in line.lower():
            return line.strip()
    return None


def _safe_extract_text(page: Any) -> str:
    """Extract page text while tolerating backend quirks."""
    try:
        return (page.extract_text() or "").strip()
    except Exception:
        return ""


def _safe_extract_words(page: Any) -> list[dict[str, Any]]:
    """Extract positioned words while tolerating backend quirks."""
    if not hasattr(page, "extract_words"):
        return []
    try:
        return page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
    except Exception:
        return []


def _safe_extract_chars(page: Any) -> list[dict[str, Any]]:
    """Extract positioned chars while tolerating backend quirks."""
    try:
        return getattr(page, "chars", []) or []
    except Exception:
        return []


def _extract_nearby_caption(page: Any, bbox: tuple[float, float, float, float] | None) -> str | None:
    """Extract nearby caption text from above the table when available."""
    page_text = _safe_extract_text(page)
    fallback = _find_table_line(page_text)
    if bbox is None or not hasattr(page, "crop"):
        return fallback
    top = bbox[1]
    crop_bbox = (0.0, max(0.0, top - 90.0), float(getattr(page, "width", bbox[2])), top)
    try:
        cropped_text = _safe_extract_text(page.crop(crop_bbox))
    except Exception:
        cropped_text = ""
    return cropped_text or fallback


def _page_rule_segments(page: Any) -> list[tuple[float, float, float, float]]:
    """Normalize raw page line geometry into generic segments."""
    try:
        raw_lines = getattr(page, "lines", []) or []
    except Exception:
        return []
    segments: list[tuple[float, float, float, float]] = []
    for line in raw_lines:
        segments.append(
            (
                float(line.get("x0", 0.0)),
                float(line.get("y0", 0.0)),
                float(line.get("x1", 0.0)),
                float(line.get("y1", line.get("y0", 0.0))),
            )
        )
    return segments


def score_candidate(candidate: DetectedTableCandidate) -> DetectedTableCandidate:
    """Assign a Table 1 likelihood score to an extracted table candidate."""
    nearby_text = " ".join(part for part in [candidate.caption or "", candidate.page_text or ""] if part)
    caption_match = bool(TABLE_1_PATTERN.search(nearby_text))
    first_column_text_ratio = _text_ratio([row[0] for row in candidate.raw_rows if row])
    later_column_numeric_ratio = _numeric_ratio(_flatten_later_columns(candidate.raw_rows))
    rectangular = bool(candidate.metadata.get("is_rectangular", False))
    min_shape = len(candidate.raw_rows) >= 2 and max((len(row) for row in candidate.raw_rows), default=0) >= 2

    score = 0.45 * caption_match
    score += 0.25 if first_column_text_ratio >= 0.6 else 0.0
    score += 0.2 if later_column_numeric_ratio >= 0.5 else 0.0
    score += 0.1 if rectangular else 0.0
    score += 0.05 if min_shape else 0.0
    return candidate.model_copy(
        update={
            "score": min(score, 1.0),
            "metadata": {
                **candidate.metadata,
                "signals": {
                    "caption_match": caption_match,
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
    rule_segments = _page_rule_segments(page)
    raw_tables = page.find_tables() if hasattr(page, "find_tables") else []
    candidates: list[DetectedTableCandidate] = []
    if raw_tables:
        for table_index, table in enumerate(raw_tables):
            raw_rows = table.extract() if hasattr(table, "extract") else table
            bbox = getattr(table, "bbox", None)
            candidates.append(
                score_candidate(
                    DetectedTableCandidate(
                        page_num=page_num,
                        table_index=table_index,
                        bbox=bbox,
                        raw_rows=_normalize_rows(raw_rows),
                        caption=_extract_nearby_caption(page, bbox),
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
        for table_index, raw_rows in enumerate(page.extract_tables() or []):
            candidates.append(
                score_candidate(
                    DetectedTableCandidate(
                        page_num=page_num,
                        table_index=table_index,
                        raw_rows=_normalize_rows(raw_rows),
                        caption=_find_table_line(page_text),
                        page_text=page_text,
                        metadata={"is_rectangular": _is_rectangular(raw_rows)},
                    )
                )
            )
    if candidates:
        return candidates

    return build_text_layout_candidates(
        page_num=page_num,
        page_text=page_text,
        words=_safe_extract_words(page),
        chars=_safe_extract_chars(page),
        rule_segments=rule_segments,
    )


def detect_table_candidates(pdf: Any) -> list[DetectedTableCandidate]:
    """Detect and score table candidates across the entire PDF."""
    candidates: list[DetectedTableCandidate] = []
    for page_num, page in enumerate(pdf.pages, start=1):
        candidates.extend(detect_page_candidates(page, page_num))
    return candidates


from table1_parser.extract.layout_fallback import _build_rows_from_line_segment, _restore_word_text
