"""PDF loading utilities for extraction backends."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def _import_pdfplumber() -> Any:
    """Import pdfplumber lazily so the package imports without the backend installed."""
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pdfplumber is required for the pdfplumber extraction backend."
        ) from exc
    return pdfplumber


@contextmanager
def open_pdf(pdf_path: str) -> Iterator[Any]:
    """Open a PDF document with pdfplumber."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pdfplumber = _import_pdfplumber()
    with pdfplumber.open(path) as pdf:
        yield pdf
