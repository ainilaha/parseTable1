"""PyMuPDF4LLM-backed paper markdown extraction."""

from __future__ import annotations

import contextlib
import io
from typing import Any


def _import_pymupdf4llm() -> Any:
    """Import pymupdf4llm lazily."""
    try:
        import pymupdf4llm
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("pymupdf4llm is required for paper markdown extraction.") from exc
    return pymupdf4llm


def extract_paper_markdown(pdf_path: str) -> str:
    """Extract markdown for a PDF while suppressing library stdout."""
    stdout_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer):
        markdown = _import_pymupdf4llm().to_markdown(pdf_path)
    return str(markdown or "")
