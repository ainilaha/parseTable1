"""pdfplumber-based extraction backend."""

from __future__ import annotations

from pathlib import Path

from table1_parser.config import Settings
from table1_parser.extract.base import BaseExtractor
from table1_parser.extract.pdf_loader import open_pdf
from table1_parser.extract.table_detector import DetectedTableCandidate, detect_table_candidates
from table1_parser.extract.table_selector import select_top_candidates
from table1_parser.schemas import ExtractedTable, TableCell


class PDFPlumberExtractor(BaseExtractor):
    """Extract raw table grids from PDFs using pdfplumber."""

    backend_name = "pdfplumber"

    def __init__(
        self,
        max_candidates: int | None = None,
        heuristic_confidence_threshold: float | None = None,
    ) -> None:
        settings = Settings()
        self.max_candidates = max_candidates or settings.max_table_candidates
        self.heuristic_confidence_threshold = (
            heuristic_confidence_threshold
            if heuristic_confidence_threshold is not None
            else settings.heuristic_confidence_threshold
        )

    def extract(self, pdf_path: str) -> list[ExtractedTable]:
        """Extract and rank raw table candidates from a PDF."""
        with open_pdf(pdf_path) as pdf:
            candidates = detect_table_candidates(pdf)

        selected_candidates = select_top_candidates(
            candidates=candidates,
            max_candidates=self.max_candidates,
            confidence_threshold=self.heuristic_confidence_threshold,
        )
        return [
            self._build_extracted_table(pdf_path=pdf_path, candidate=candidate)
            for candidate in selected_candidates
        ]

    def _build_extracted_table(
        self,
        pdf_path: str,
        candidate: DetectedTableCandidate,
    ) -> ExtractedTable:
        """Convert a detected candidate into the canonical extracted-table schema."""
        title, caption = _split_caption(candidate.caption)
        cells: list[TableCell] = []
        for row_idx, row in enumerate(candidate.raw_rows):
            for col_idx, cell_text in enumerate(row):
                cells.append(
                    TableCell(
                        row_idx=row_idx,
                        col_idx=col_idx,
                        text=cell_text,
                        page_num=candidate.page_num,
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
