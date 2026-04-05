"""PyMuPDF4LLM-backed paper markdown extraction."""

from __future__ import annotations

import contextlib
import io

from table1_parser.text_cleaning import repair_extractor_glyph_failures


def extract_paper_markdown(pdf_path: str) -> str:
    """Extract markdown for a PDF while suppressing library stdout."""
    try:
        import pymupdf4llm
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("pymupdf4llm is required for paper markdown extraction.") from exc
    stdout_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer):
        markdown = pymupdf4llm.to_markdown(pdf_path)
    return repair_extractor_glyph_failures(str(markdown or ""))
