"""Backend-agnostic helpers for geometry-driven table fallback extraction."""

from __future__ import annotations

import re

from table1_parser.extract.table_detector import (
    DetectedTableCandidate,
    _is_rectangular,
    _normalize_rows,
    score_candidate,
)


ALPHA_TOKEN_PATTERN = re.compile(r"[A-Za-z]")
NUMERIC_TOKEN_PATTERN = re.compile(r"\d")
TABLE_CAPTION_PATTERN = re.compile(r"^\s*table\s*\d+\b(?:\s*[:.])?", re.IGNORECASE)
LINE_MERGE_TOLERANCE = 4.0
COLUMN_CLUSTER_TOLERANCE = 18.0
COLLAPSED_LABEL_PATTERN = re.compile(r"[a-z][A-Z]|[A-Za-z-]{8,}")


def detect_horizontal_rules(
    rule_segments: list[tuple[float, float, float, float]] | None,
    bbox: tuple[float, float, float, float] | None,
) -> list[float]:
    """Detect wide horizontal rules spanning most of the candidate table width."""
    if bbox is None or not rule_segments:
        return []

    left, top, right, bottom = bbox
    table_width = max(1.0, float(right) - float(left))
    rule_positions: list[float] = []
    for x0, y0, x1, y1 in rule_segments:
        if abs(y1 - y0) > 1.5:
            continue
        if y0 < top - 12.0 or y0 > bottom + 12.0:
            continue
        overlap_left = max(float(left), min(x0, x1))
        overlap_right = min(float(right), max(x0, x1))
        if overlap_right <= overlap_left:
            continue
        if (overlap_right - overlap_left) / table_width < 0.8:
            continue
        rule_positions.append(y0)

    deduped: list[float] = []
    for value in sorted(rule_positions):
        if not deduped or abs(value - deduped[-1]) > 3.0:
            deduped.append(value)
    return deduped


def _is_numeric_like(text: str) -> bool:
    """Return whether a token looks numeric enough to be a table value."""
    return bool(NUMERIC_TOKEN_PATTERN.search(text))


def _build_rows_from_line_segment(
    lines: list[dict[str, object]],
    page_chars: list[dict[str, object]] | None = None,
) -> list[list[str]]:
    """Convert a line segment into a row-major grid using x-position anchors."""
    numeric_positions = sorted(
        float(word["x0"])
        for line in lines
        for word in line["words"]
        if _is_numeric_like(str(word["text"]))
    )
    if not numeric_positions:
        numeric_anchors = []
    else:
        clusters: list[list[float]] = [[numeric_positions[0]]]
        for position in numeric_positions[1:]:
            if abs(position - clusters[-1][-1]) <= COLUMN_CLUSTER_TOLERANCE:
                clusters[-1].append(position)
            else:
                clusters.append([position])
        numeric_anchors = [sum(cluster) / len(cluster) for cluster in clusters]
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
            column_index = 0
            while column_index < len(boundaries) and float(word["x0"]) >= boundaries[column_index]:
                column_index += 1
            if (
                column_index <= 1
                and " " not in text
                and ALPHA_TOKEN_PATTERN.search(text)
                and not NUMERIC_TOKEN_PATTERN.search(text)
                and COLLAPSED_LABEL_PATTERN.search(text)
            ):
                if page_chars:
                    x0 = float(word["x0"])
                    x1 = float(word["x1"])
                    top = float(word["top"])
                    bottom = float(word["bottom"])
                    chars_in_word = [
                        char
                        for char in page_chars
                        if float(char["x0"]) >= x0 - 0.5
                        and float(char["x1"]) <= x1 + 0.5
                        and min(bottom, float(char["bottom"])) >= max(top, float(char["top"]))
                    ]
                    if chars_in_word:
                        ordered_chars = sorted(chars_in_word, key=lambda char: float(char["x0"]))
                        pieces: list[str] = []
                        previous_char: dict[str, object] | None = None
                        for char in ordered_chars:
                            char_text = str(char.get("text", ""))
                            if not char_text:
                                continue
                            if previous_char is not None:
                                gap = float(char["x0"]) - float(previous_char["x1"])
                                previous_width = float(previous_char["x1"]) - float(previous_char["x0"])
                                current_width = float(char["x1"]) - float(char["x0"])
                                gap_threshold = max(1.5, min(previous_width, current_width) * 0.6)
                                previous_text = str(previous_char.get("text", ""))
                                if previous_text.isalpha() and char_text.isalpha() and (previous_text.islower() or char_text.isupper()):
                                    gap_threshold = min(gap_threshold, max(1.2, min(previous_width, current_width) * 0.45))
                                if gap > gap_threshold:
                                    pieces.append(" ")
                            pieces.append(char_text)
                            previous_char = char
                        restored = "".join(pieces).strip()
                        if restored:
                            text = restored
            row_cells[column_index] = f"{row_cells[column_index]} {text}".strip()
        rows.append(row_cells)
    return _normalize_rows(rows)


def build_text_layout_candidates(
    *,
    page_num: int,
    page_text: str,
    words: list[dict[str, object]],
    chars: list[dict[str, object]] | None = None,
    rule_segments: list[tuple[float, float, float, float]] | None = None,
    layout_source: str = "text_positions",
) -> list[DetectedTableCandidate]:
    """Build scored candidates from page word and char geometry."""
    page_chars = chars or []
    if not words:
        lines = []
    else:
        lines = []
        for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
            top = float(word["top"])
            bottom = float(word["bottom"])
            if not lines or abs(top - float(lines[-1]["top"])) > LINE_MERGE_TOLERANCE:
                lines.append({"top": top, "bottom": bottom, "words": [word]})
                continue
            lines[-1]["words"].append(word)
            lines[-1]["bottom"] = max(float(lines[-1]["bottom"]), bottom)
        for line in lines:
            line["words"] = sorted(line["words"], key=lambda item: float(item["x0"]))
            line["text"] = " ".join(str(word["text"]).strip() for word in line["words"]).strip()

    caption_indices = [index for index, line in enumerate(lines) if TABLE_CAPTION_PATTERN.search(str(line["text"]))]
    candidates: list[DetectedTableCandidate] = []
    segments: list[dict[str, object]] = []
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
        segments.append(
            {
                "caption": "\n".join(caption_parts),
                "content_lines": content_lines,
                "row_bounds": [(float(line["top"]), float(line["bottom"])) for line in content_lines],
                "bbox": (left, float(segment_lines[0]["top"]), right, max(float(line["bottom"]) for line in content_lines)),
            }
        )
    for table_index, segment in enumerate(segments):
        raw_rows = _build_rows_from_line_segment(segment["content_lines"], page_chars=page_chars)
        bbox = segment["bbox"]
        candidates.append(
            score_candidate(
                DetectedTableCandidate(
                    page_num=page_num,
                    table_index=table_index,
                    bbox=bbox,
                    raw_rows=raw_rows,
                    caption=segment["caption"],
                    page_text=page_text,
                    metadata={
                        "is_rectangular": _is_rectangular(raw_rows),
                        "layout_source": layout_source,
                        "row_bounds": segment["row_bounds"],
                        "horizontal_rules": detect_horizontal_rules(rule_segments, bbox),
                    },
                )
            )
        )
    return candidates
