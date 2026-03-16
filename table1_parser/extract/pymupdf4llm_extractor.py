"""PyMuPDF4LLM-based extraction backend with pdfplumber fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from table1_parser.config import Settings
from table1_parser.extract.base import BaseExtractor
from table1_parser.extract.pdfplumber_extractor import PDFPlumberExtractor
from table1_parser.extract.table_detector import DetectedTableCandidate, _normalize_rows, score_candidate
from table1_parser.extract.table_selector import select_top_candidates
from table1_parser.schemas import ExtractedTable, TableCell


def _import_pymupdf4llm() -> Any:
    """Import pymupdf4llm lazily so the package imports without it installed."""
    try:
        import pymupdf4llm
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pymupdf4llm is required for the pymupdf4llm extraction backend."
        ) from exc
    return pymupdf4llm


class PyMuPDF4LLMExtractor(BaseExtractor):
    """Extract raw table grids with PyMuPDF4LLM and fall back to pdfplumber when needed."""

    backend_name = "pymupdf4llm"

    def __init__(
        self,
        max_candidates: int | None = None,
        heuristic_confidence_threshold: float | None = None,
        fallback_extractor: BaseExtractor | None = None,
    ) -> None:
        settings = Settings()
        self.max_candidates = max_candidates or settings.max_table_candidates
        self.heuristic_confidence_threshold = (
            heuristic_confidence_threshold
            if heuristic_confidence_threshold is not None
            else settings.heuristic_confidence_threshold
        )
        self.fallback_extractor = fallback_extractor or PDFPlumberExtractor(
            max_candidates=self.max_candidates,
            heuristic_confidence_threshold=self.heuristic_confidence_threshold,
        )

    def extract(self, pdf_path: str) -> list[ExtractedTable]:
        """Extract and rank raw table candidates from a PDF."""
        try:
            candidates = self._detect_table_candidates(pdf_path)
        except Exception:
            return self._extract_with_fallback(pdf_path, reason="primary_error")

        if not candidates:
            return self._extract_with_fallback(pdf_path, reason="no_candidates")

        selected_candidates = select_top_candidates(
            candidates=candidates,
            max_candidates=self.max_candidates,
            confidence_threshold=self.heuristic_confidence_threshold,
        )
        if not selected_candidates:
            return self._extract_with_fallback(pdf_path, reason="below_threshold")

        return [
            self._build_extracted_table(pdf_path=pdf_path, candidate=candidate)
            for candidate in selected_candidates
        ]

    def _detect_table_candidates(self, pdf_path: str) -> list[DetectedTableCandidate]:
        pymupdf4llm = _import_pymupdf4llm()
        payload = json.loads(pymupdf4llm.to_json(pdf_path))
        pages = payload.get("pages", [])
        candidates: list[DetectedTableCandidate] = []
        for page in pages:
            page_num = int(page.get("page_number", 0))
            page_boxes = page.get("boxes", []) or []
            page_text = _collect_page_text(page_boxes)
            table_boxes = [box for box in page_boxes if isinstance(box, dict) and box.get("table")]
            for table_index, box in enumerate(table_boxes):
                table = box.get("table") or {}
                raw_rows = _normalize_rows(table.get("extract") or [])
                if not raw_rows:
                    continue
                bbox = _as_bbox(table.get("bbox")) or _as_bbox(box.get("bbox"))
                cell_bboxes = _coerce_cell_bboxes(table.get("cells") or [])
                row_bounds, horizontal_rules = _derive_row_geometry(cell_bboxes, bbox)
                caption = _find_nearby_caption(page_boxes=page_boxes, table_bbox=bbox)
                candidate = DetectedTableCandidate(
                    page_num=page_num,
                    table_index=table_index,
                    bbox=bbox,
                    raw_rows=raw_rows,
                    caption=caption,
                    page_text=page_text,
                    metadata={
                        "layout_source": "pymupdf4llm_json",
                        "primary_representation": "json",
                        "extractor_used": self.backend_name,
                        "fallback_used": False,
                        "row_count": table.get("row_count"),
                        "col_count": table.get("col_count"),
                        "table_markdown": table.get("markdown"),
                        "table_cells": table.get("cells"),
                        "row_bounds": row_bounds,
                        "horizontal_rules": horizontal_rules,
                    },
                )
                candidates.append(score_candidate(candidate))
        return candidates

    def _build_extracted_table(
        self,
        pdf_path: str,
        candidate: DetectedTableCandidate,
    ) -> ExtractedTable:
        title, caption = _split_caption(candidate.caption)
        cells: list[TableCell] = []
        table_cells = candidate.metadata.get("table_cells") or []
        cell_bboxes = _coerce_cell_bboxes(table_cells)
        for row_idx, row in enumerate(candidate.raw_rows):
            for col_idx, cell_text in enumerate(row):
                bbox = None
                if row_idx < len(cell_bboxes) and col_idx < len(cell_bboxes[row_idx]):
                    bbox = cell_bboxes[row_idx][col_idx]
                cells.append(
                    TableCell(
                        row_idx=row_idx,
                        col_idx=col_idx,
                        text=cell_text,
                        page_num=candidate.page_num,
                        bbox=bbox,
                        extractor_name=self.backend_name,
                        confidence=candidate.score,
                    )
                )

        metadata = {
            **candidate.metadata,
            "bbox": candidate.bbox,
            "candidate_score": candidate.score,
        }
        return ExtractedTable(
            table_id=_build_table_id(pdf_path=pdf_path, candidate=candidate),
            source_pdf=pdf_path,
            page_num=candidate.page_num,
            title=title,
            caption=caption,
            n_rows=len(candidate.raw_rows),
            n_cols=max((len(row) for row in candidate.raw_rows), default=0),
            cells=cells,
            extraction_backend=self.backend_name,
            metadata=metadata,
        )

    def _extract_with_fallback(self, pdf_path: str, reason: str) -> list[ExtractedTable]:
        tables = self.fallback_extractor.extract(pdf_path)
        for table in tables:
            table.metadata.setdefault("primary_representation", "json")
            table.metadata["extractor_used"] = self.backend_name
            table.metadata["fallback_backend"] = getattr(self.fallback_extractor, "backend_name", "unknown")
            table.metadata["fallback_reason"] = reason
            table.metadata["fallback_used"] = True
        return tables


def _collect_page_text(page_boxes: list[dict[str, Any]]) -> str:
    """Collect page text from non-table content boxes."""
    texts = []
    for box in page_boxes:
        if box.get("boxclass") == "table":
            continue
        text = _extract_box_text(box)
        if text:
            texts.append(text)
    return "\n".join(texts)


def _extract_box_text(box: dict[str, Any]) -> str:
    """Read text from a PyMuPDF4LLM box."""
    textlines = box.get("textlines") or []
    lines: list[str] = []
    for line in textlines:
        spans = line.get("spans") or []
        line_text = "".join(str(span.get("text", "")) for span in spans).strip()
        if line_text:
            lines.append(line_text)
    return " ".join(lines).strip()


def _find_nearby_caption(
    *,
    page_boxes: list[dict[str, Any]],
    table_bbox: tuple[float, float, float, float] | None,
) -> str | None:
    """Find the nearest preceding Table-caption-like box on the same page."""
    candidates: list[tuple[float, str]] = []
    table_top = table_bbox[1] if table_bbox else float("inf")
    for box in page_boxes:
        if box.get("boxclass") == "table":
            continue
        bbox = _as_bbox(box.get("bbox"))
        if bbox is None or bbox[3] > table_top + 2.0:
            continue
        text = _extract_box_text(box)
        if not text or "table" not in text.lower():
            continue
        candidates.append((table_top - bbox[3], text))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def _as_bbox(value: Any) -> tuple[float, float, float, float] | None:
    """Convert a raw bbox-like value to a tuple."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    return tuple(float(part) for part in value)


def _coerce_cell_bboxes(table_cells: list[Any]) -> list[list[tuple[float, float, float, float] | None]]:
    """Normalize PyMuPDF4LLM cell bbox arrays into row-major bbox lists."""
    rows: list[list[tuple[float, float, float, float] | None]] = []
    for row in table_cells:
        if not isinstance(row, list):
            continue
        bbox_row: list[tuple[float, float, float, float] | None] = []
        for cell in row:
            bbox_row.append(_as_bbox(cell))
        rows.append(bbox_row)
    return rows


def _derive_row_geometry(
    cell_bboxes: list[list[tuple[float, float, float, float] | None]],
    table_bbox: tuple[float, float, float, float] | None,
) -> tuple[list[tuple[float, float]], list[float]]:
    """Derive row bounds and row-spanning horizontal boundaries from cell geometry."""
    row_bounds: list[tuple[float, float]] = []
    rule_positions: list[float] = []
    table_width = None
    if table_bbox is not None:
        table_width = max(1.0, table_bbox[2] - table_bbox[0])

    for row in cell_bboxes:
        populated = [bbox for bbox in row if bbox is not None]
        if not populated:
            continue
        row_top = min(bbox[1] for bbox in populated)
        row_bottom = max(bbox[3] for bbox in populated)
        row_bounds.append((row_top, row_bottom))

        row_left = min(bbox[0] for bbox in populated)
        row_right = max(bbox[2] for bbox in populated)
        if table_width is None:
            coverage_ok = len(populated) >= max(2, len(row) // 2)
        else:
            coverage_ok = ((row_right - row_left) / table_width) >= 0.8
        if coverage_ok:
            rule_positions.extend([row_top, row_bottom])

    deduped_rules: list[float] = []
    for value in sorted(rule_positions):
        if not deduped_rules or abs(value - deduped_rules[-1]) > 1.5:
            deduped_rules.append(value)
    return row_bounds, deduped_rules


def _build_table_id(pdf_path: str, candidate: DetectedTableCandidate) -> str:
    """Build a stable table identifier from PDF and page context."""
    stem = Path(pdf_path).stem
    return f"{stem}-p{candidate.page_num}-t{candidate.table_index}"


def _split_caption(caption: str | None) -> tuple[str | None, str | None]:
    """Split nearby caption text into title and caption fields."""
    if not caption:
        return None, None

    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    if not lines:
        return None, None

    title = lines[0]
    if len(lines) == 1:
        return title, title
    return title, " ".join(lines)
