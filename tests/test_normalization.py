"""Normalization layer tests for Phase 3."""

from __future__ import annotations

from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.header_detector import detect_header_rows
from table1_parser.normalize.pipeline import normalize_extracted_table
from table1_parser.normalize.row_signature import build_row_signature
from table1_parser.normalize.text_normalizer import alpha_only_text, normalize_label_text
from table1_parser.schemas import ExtractedTable, TableCell


def test_clean_text_collapses_whitespace_and_normalizes_dashes() -> None:
    """Cleaning should normalize repeated whitespace and dash variants."""
    assert clean_text("  Age   -  years  ") == "Age - years"
    assert clean_text("BMI\u2013kg/m2") == "BMI-kg/m2"


def test_label_normalization_preserves_alphanumerics() -> None:
    """Normalized label text should retain letters and digits while dropping punctuation."""
    assert normalize_label_text("High school") == "High school"
    assert normalize_label_text("Family poverty-income ratio") == "Family poverty income ratio"
    assert normalize_label_text("Non-hispanic white") == "Non hispanic white"
    assert normalize_label_text("Hispanic/Mexican") == "Hispanic Mexican"
    assert normalize_label_text("More than high school") == "More than high school"
    assert normalize_label_text("Age, years") == "Age years"
    assert normalize_label_text("BMI, kg/m2") == "BMI kg m2"
    assert normalize_label_text("<HS") == "HS"


def test_alpha_only_conversion_drops_symbols_and_digits() -> None:
    """Alpha-only text should preserve only alphabetic tokens."""
    assert alpha_only_text("High school") == "High school"
    assert alpha_only_text("Family poverty-income ratio") == "Family poverty income ratio"
    assert alpha_only_text("Non-hispanic white") == "Non hispanic white"
    assert alpha_only_text("Hispanic/Mexican") == "Hispanic Mexican"
    assert alpha_only_text("More than high school") == "More than high school"
    assert alpha_only_text("Age, years") == "Age years"
    assert alpha_only_text("<HS") == "HS"
    assert alpha_only_text("BMI, kg/m2") == "BMI kg m"


def test_header_detector_prefers_top_text_heavy_rows() -> None:
    """Header detection should classify top metadata rows separately from the body."""
    rows = [
        ["Variable", "Overall (n=100)", "P-value"],
        ["Age, years", "52.1", "0.03"],
        ["Male", "34", "0.10"],
    ]

    header_rows, body_rows = detect_header_rows(rows)

    assert header_rows == [0]
    assert body_rows == [1, 2]


def test_row_signature_generation_keeps_raw_and_normalized_forms() -> None:
    """Row signatures should preserve raw text while deriving normalized first-column features."""
    row_view = build_row_signature(1, ["  <HS", "34", "45%"])

    assert row_view.first_cell_raw == "  <HS"
    assert row_view.first_cell_normalized == "HS"
    assert row_view.first_cell_alpha_only == "HS"
    assert row_view.numeric_cell_count == 2
    assert row_view.has_trailing_values is True
    assert row_view.indent_level == 2
    assert row_view.likely_role is None


def test_row_signature_prefers_bbox_indent_when_available() -> None:
    """Bounding-box indentation should override literal leading spaces when present."""
    row_view = build_row_signature(
        1,
        ["  Hispanic/Mexican", "34"],
        first_cell_bbox=(18.0, 0.0, 30.0, 10.0),
        base_x0=10.0,
    )

    assert row_view.first_cell_raw == "  Hispanic/Mexican"
    assert row_view.first_cell_normalized == "Hispanic Mexican"
    assert row_view.indent_level == 8


def test_row_signature_preserves_raw_text_word_boundaries() -> None:
    """Row signatures should keep the raw string untouched while normalizing separately."""
    row_view = build_row_signature(1, ["High school", "34"])

    assert row_view.first_cell_raw == "High school"
    assert row_view.first_cell_normalized == "High school"
    assert row_view.first_cell_alpha_only == "High school"


def test_extracted_table_to_normalized_table_conversion() -> None:
    """Normalization should convert extracted rows into a NormalizedTable view."""
    extracted = ExtractedTable(
        table_id="tbl-1",
        source_pdf="paper.pdf",
        page_num=1,
        title="Table 1",
        caption="Baseline characteristics",
        n_rows=3,
        n_cols=3,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable"),
            TableCell(row_idx=0, col_idx=1, text="Overall (n=100)"),
            TableCell(row_idx=0, col_idx=2, text="P-value"),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
            TableCell(row_idx=1, col_idx=2, text="0.03"),
            TableCell(row_idx=2, col_idx=0, text="Male"),
            TableCell(row_idx=2, col_idx=1, text="34"),
            TableCell(row_idx=2, col_idx=2, text="0.10"),
        ],
        extraction_backend="pdfplumber",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.header_rows == [0]
    assert normalized.body_rows == [1, 2]
    assert normalized.row_views[0].first_cell_normalized == "Age years"
    assert normalized.row_views[1].first_cell_alpha_only == "Male"
    assert normalized.metadata["extraction_backend"] == "pdfplumber"
