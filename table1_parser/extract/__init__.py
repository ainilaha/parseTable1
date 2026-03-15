"""Extraction backends and helpers."""

from table1_parser.extract.base import BaseExtractor
from table1_parser.extract.pdfplumber_extractor import PDFPlumberExtractor


def build_extractor(backend_name: str = "pdfplumber") -> BaseExtractor:
    """Create an extraction backend from its configured name."""
    if backend_name == "pdfplumber":
        return PDFPlumberExtractor()
    raise ValueError(f"Unsupported extraction backend: {backend_name}")


__all__ = ["BaseExtractor", "PDFPlumberExtractor", "build_extractor"]
