"""Synthetic document generation helpers."""

from table1_parser.synthetic.generator import generate_synthetic_document
from table1_parser.synthetic.html_renderer import render_html_document
from table1_parser.synthetic.pdf_renderer import render_pdf_from_html
from table1_parser.synthetic.spec_models import SyntheticDocumentSpec, load_table_spec
from table1_parser.synthetic.truth_writer import build_truth_json

__all__ = [
    "SyntheticDocumentSpec",
    "build_truth_json",
    "generate_synthetic_document",
    "load_table_spec",
    "render_html_document",
    "render_pdf_from_html",
]
