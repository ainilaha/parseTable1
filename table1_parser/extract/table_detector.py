"""Heuristics for identifying likely Table 1 candidates in a PDF."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


TABLE_1_PATTERN = re.compile(r"\btable\s*1\b", re.IGNORECASE)
TABLE_CAPTION_PATTERN = re.compile(r"\btable\s*\d+\b", re.IGNORECASE)
NUMERIC_TOKEN_PATTERN = re.compile(r"\d")
ALPHA_TOKEN_PATTERN = re.compile(r"[A-Za-z]")
LINE_MERGE_TOLERANCE = 4.0
COLUMN_CLUSTER_TOLERANCE = 18.0


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
    if value is None:
        return ""
    return str(value).strip()


def _normalize_rows(raw_rows: list[list[Any]]) -> list[list[str]]:
    """Normalize a raw table grid and pad rows into a rectangle."""
    if not raw_rows:
        return []

    max_cols = max((len(row) for row in raw_rows), default=0)
    normalized_rows: list[list[str]] = []
    for row in raw_rows:
        normalized_row = [_normalize_cell(cell) for cell in row]
        normalized_row.extend([""] * (max_cols - len(normalized_row)))
        normalized_rows.append(normalized_row)
    return normalized_rows


def _is_rectangular(raw_rows: list[list[Any]]) -> bool:
    """Return whether all rows in the extracted grid have the same width."""
    row_lengths = {len(row) for row in raw_rows if row}
    return bool(row_lengths) and len(row_lengths) == 1


def _text_ratio(values: list[str]) -> float:
    """Measure how many populated cells contain alphabetic content."""
    populated = [value for value in values if value.strip()]
    if not populated:
        return 0.0
    text_like = [value for value in populated if ALPHA_TOKEN_PATTERN.search(value)]
    return len(text_like) / len(populated)


def _numeric_ratio(values: list[str]) -> float:
    """Measure how many populated cells contain numeric content."""
    populated = [value for value in values if value.strip()]
    if not populated:
        return 0.0
    numeric_like = [value for value in populated if NUMERIC_TOKEN_PATTERN.search(value)]
    return len(numeric_like) / len(populated)


def _flatten_later_columns(raw_rows: list[list[str]]) -> list[str]:
    """Collect non-first-column cells across the table."""
    return [cell for row in raw_rows for cell in row[1:]]


def _extract_nearby_caption(page: Any, bbox: tuple[float, float, float, float] | None) -> str | None:
    """Extract nearby caption text from above the table when available."""
    page_text = _safe_extract_text(page)
    fallback = _find_table_line(page_text)
    if bbox is None or not hasattr(page, "crop"):
        return fallback

    top = bbox[1]
    page_width = float(getattr(page, "width", bbox[2]))
    crop_bbox = (0.0, max(0.0, top - 90.0), page_width, top)
    try:
        cropped_page = page.crop(crop_bbox)
        cropped_text = _safe_extract_text(cropped_page)
    except Exception:
        cropped_text = ""
    return cropped_text or fallback


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


def _group_words_into_lines(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group positioned words into reading-order lines."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda word: (float(word["top"]), float(word["x0"])))
    lines: list[dict[str, Any]] = []

    for word in sorted_words:
        top = float(word["top"])
        bottom = float(word["bottom"])
        if not lines or abs(top - float(lines[-1]["top"])) > LINE_MERGE_TOLERANCE:
            lines.append({"top": top, "bottom": bottom, "words": [word]})
            continue

        lines[-1]["words"].append(word)
        lines[-1]["bottom"] = max(float(lines[-1]["bottom"]), bottom)

    for line in lines:
        line["words"] = sorted(line["words"], key=lambda word: float(word["x0"]))
        line["text"] = " ".join(str(word["text"]).strip() for word in line["words"]).strip()
    return lines


def _cluster_positions(positions: list[float], tolerance: float) -> list[float]:
    """Cluster x positions into stable column anchors."""
    if not positions:
        return []

    clusters: list[list[float]] = [[positions[0]]]
    for position in positions[1:]:
        if abs(position - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(position)
        else:
            clusters.append([position])
    return [sum(cluster) / len(cluster) for cluster in clusters]


def _is_numeric_like(text: str) -> bool:
    """Return whether a token looks numeric enough to be a table value."""
    return bool(NUMERIC_TOKEN_PATTERN.search(text))


def _build_rows_from_line_segment(lines: list[dict[str, Any]]) -> list[list[str]]:
    """Convert a line segment into a row-major grid using x-position anchors."""
    numeric_positions = sorted(
        float(word["x0"])
        for line in lines
        for word in line["words"]
        if _is_numeric_like(str(word["text"]))
    )
    numeric_anchors = _cluster_positions(numeric_positions, COLUMN_CLUSTER_TOLERANCE)

    if not numeric_anchors:
        return []

    boundaries = [
        (numeric_anchors[index] + numeric_anchors[index + 1]) / 2.0
        for index in range(len(numeric_anchors) - 1)
    ]

    rows: list[list[str]] = []
    for line in lines:
        row_cells = [""] * (len(numeric_anchors) + 1)
        for word in line["words"]:
            text = str(word["text"]).strip()
            x0 = float(word["x0"])
            column_index = 0
            while column_index < len(boundaries) and x0 >= boundaries[column_index]:
                column_index += 1
            if row_cells[column_index]:
                row_cells[column_index] = f"{row_cells[column_index]} {text}"
            else:
                row_cells[column_index] = text
        rows.append([cell.strip() for cell in row_cells])
    return _normalize_rows(rows)


def _segment_lines_into_tables(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split page lines into table-like segments starting at caption lines."""
    caption_indices = [
        index for index, line in enumerate(lines) if TABLE_CAPTION_PATTERN.search(str(line["text"]))
    ]
    if not caption_indices:
        return []

    segments: list[dict[str, Any]] = []
    for segment_index, start_index in enumerate(caption_indices):
        end_index = caption_indices[segment_index + 1] if segment_index + 1 < len(caption_indices) else len(lines)
        segment_lines = lines[start_index:end_index]
        if len(segment_lines) < 3:
            continue

        caption_parts = [str(segment_lines[0]["text"]).strip()]
        content_start = 1
        if len(segment_lines) > 1:
            second_line_text = str(segment_lines[1]["text"]).strip()
            second_line_word_count = len(segment_lines[1]["words"])
            if second_line_text and second_line_word_count <= 2 and not _is_numeric_like(second_line_text):
                caption_parts.append(second_line_text)
                content_start = 2

        content_lines = segment_lines[content_start:]
        rows = _build_rows_from_line_segment(content_lines)
        if not rows:
            continue

        left = min(float(word["x0"]) for line in content_lines for word in line["words"])
        right = max(float(word["x1"]) for line in content_lines for word in line["words"])
        top = float(segment_lines[0]["top"])
        bottom = max(float(line["bottom"]) for line in content_lines)
        segments.append(
            {
                "caption": "\n".join(caption_parts),
                "rows": rows,
                "bbox": (left, top, right, bottom),
            }
        )
    return segments


def _fallback_text_layout_candidates(page: Any, page_num: int, page_text: str) -> list[DetectedTableCandidate]:
    """Build fallback candidates from word positions when grid detection fails."""
    lines = _group_words_into_lines(_safe_extract_words(page))
    segments = _segment_lines_into_tables(lines)
    candidates: list[DetectedTableCandidate] = []

    for table_index, segment in enumerate(segments):
        raw_rows = segment["rows"]
        candidate = DetectedTableCandidate(
            page_num=page_num,
            table_index=table_index,
            bbox=segment["bbox"],
            raw_rows=raw_rows,
            caption=segment["caption"],
            page_text=page_text,
            metadata={
                "is_rectangular": _is_rectangular(raw_rows),
                "layout_source": "text_positions",
            },
        )
        candidates.append(score_candidate(candidate))
    return candidates


def score_candidate(candidate: DetectedTableCandidate) -> DetectedTableCandidate:
    """Assign a Table 1 likelihood score to an extracted table candidate."""
    first_column = [row[0] for row in candidate.raw_rows if row]
    later_columns = _flatten_later_columns(candidate.raw_rows)
    nearby_text = " ".join(
        part for part in [candidate.caption or "", candidate.page_text or ""] if part
    )

    caption_match = bool(TABLE_1_PATTERN.search(nearby_text))
    first_column_text_ratio = _text_ratio(first_column)
    later_column_numeric_ratio = _numeric_ratio(later_columns)
    rectangular = bool(candidate.metadata.get("is_rectangular", False))
    min_shape = len(candidate.raw_rows) >= 2 and max((len(row) for row in candidate.raw_rows), default=0) >= 2

    score = 0.0
    if caption_match:
        score += 0.45
    if first_column_text_ratio >= 0.6:
        score += 0.25
    if later_column_numeric_ratio >= 0.5:
        score += 0.2
    if rectangular:
        score += 0.1
    if min_shape:
        score += 0.05

    metadata = {
        **candidate.metadata,
        "signals": {
            "caption_match": caption_match,
            "first_column_text_ratio": round(first_column_text_ratio, 4),
            "later_column_numeric_ratio": round(later_column_numeric_ratio, 4),
            "rectangular": rectangular,
        },
    }
    return candidate.model_copy(update={"score": min(score, 1.0), "metadata": metadata})


def detect_page_candidates(page: Any, page_num: int) -> list[DetectedTableCandidate]:
    """Detect raw table candidates on a single page."""
    page_text = _safe_extract_text(page)
    raw_tables = page.find_tables() if hasattr(page, "find_tables") else []
    candidates: list[DetectedTableCandidate] = []

    if raw_tables:
        for table_index, table in enumerate(raw_tables):
            raw_rows = table.extract() if hasattr(table, "extract") else table
            normalized_rows = _normalize_rows(raw_rows)
            candidate = DetectedTableCandidate(
                page_num=page_num,
                table_index=table_index,
                bbox=getattr(table, "bbox", None),
                raw_rows=normalized_rows,
                caption=_extract_nearby_caption(page, getattr(table, "bbox", None)),
                page_text=page_text,
                metadata={"is_rectangular": _is_rectangular(raw_rows)},
            )
            candidates.append(score_candidate(candidate))
        return candidates

    if hasattr(page, "extract_tables"):
        extracted_tables = page.extract_tables() or []
        for table_index, raw_rows in enumerate(extracted_tables):
            normalized_rows = _normalize_rows(raw_rows)
            candidate = DetectedTableCandidate(
                page_num=page_num,
                table_index=table_index,
                raw_rows=normalized_rows,
                caption=_find_table_line(page_text),
                page_text=page_text,
                metadata={"is_rectangular": _is_rectangular(raw_rows)},
            )
            candidates.append(score_candidate(candidate))
    if candidates:
        return candidates

    return _fallback_text_layout_candidates(page=page, page_num=page_num, page_text=page_text)


def detect_table_candidates(pdf: Any) -> list[DetectedTableCandidate]:
    """Detect and score table candidates across the entire PDF."""
    candidates: list[DetectedTableCandidate] = []
    for page_num, page in enumerate(pdf.pages, start=1):
        candidates.extend(detect_page_candidates(page, page_num))
    return candidates
