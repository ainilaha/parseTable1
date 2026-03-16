"""Extraction backends and helpers."""

from table1_parser.extract.base import BaseExtractor
from table1_parser.extract.pdfplumber_extractor import PDFPlumberExtractor
from table1_parser.extract.pymupdf4llm_extractor import PyMuPDF4LLMExtractor


def build_extractor(backend_name: str = "pymupdf4llm") -> BaseExtractor:
    """Create an extraction backend from its configured name."""
    if backend_name == "pymupdf4llm":
        return PyMuPDF4LLMExtractor()
    if backend_name == "pdfplumber":
        return PDFPlumberExtractor()
    raise ValueError(f"Unsupported extraction backend: {backend_name}")


__all__ = ["BaseExtractor", "PDFPlumberExtractor", "PyMuPDF4LLMExtractor", "build_extractor"]
