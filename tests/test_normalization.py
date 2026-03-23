"""Normalization layer tests for Phase 3."""

from __future__ import annotations

from pathlib import Path

from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.header_detector import detect_header_rows
from table1_parser.normalize.io import load_normalized_tables, normalized_tables_to_payload, write_normalized_tables
from table1_parser.normalize.pipeline import normalize_extracted_table
from table1_parser.normalize.row_signature import build_row_signature
from table1_parser.normalize.text_normalizer import alpha_only_text, normalize_label_text
from table1_parser.schemas import ExtractedTable, TableCell


def test_clean_text_collapses_whitespace_and_normalizes_dashes() -> None:
    """Cleaning should normalize repeated whitespace, comparisons, and dash variants."""
    assert clean_text("  Age   -  years  ") == "Age - years"
    assert clean_text("BMI\u2013kg/m2") == "BMI-kg/m2"
    assert clean_text("p \uff1c 0.05") == "p < 0.05"
    assert clean_text("BMI \u2265 30") == "BMI >= 30"


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


def test_header_detector_uses_horizontal_rules_as_strong_boundary_signal() -> None:
    """Wide horizontal rules should strengthen top header-boundary detection when row bounds exist."""
    rows = [
        ["Characteristic", "Overall", "P-value"],
        ["Age, years", "52.1", "0.03"],
        ["Male", "34", "0.10"],
    ]

    header_rows, body_rows = detect_header_rows(
        rows,
        row_bounds=[(12.0, 20.0), (26.0, 34.0), (40.0, 48.0)],
        horizontal_rules=[6.0, 24.0],
    )

    assert header_rows == [0]
    assert body_rows == [1, 2]


def test_header_detector_lets_strong_rules_override_weaker_text_heuristics() -> None:
    """Strong bracketing rules should win even when text-only cues would miss a second header row."""
    rows = [
        ["Characteristic", "Overall", "Cases"],
        ["", "n", "%"],
        ["Age, years", "52.1", "51.4"],
        ["Male", "34", "32"],
    ]

    header_rows, body_rows = detect_header_rows(
        rows,
        row_bounds=[(12.0, 20.0), (24.0, 32.0), (38.0, 46.0), (50.0, 58.0)],
        horizontal_rules=[7.0, 35.0],
    )

    assert header_rows == [0, 1]
    assert body_rows == [2, 3]


def test_header_detector_falls_back_when_horizontal_rules_are_missing() -> None:
    """Header detection should keep the existing heuristic behavior when no rules are available."""
    rows = [
        ["Characteristic", "Overall", "P-value"],
        ["Age, years", "52.1", "0.03"],
        ["Male", "34", "0.10"],
    ]

    header_rows, body_rows = detect_header_rows(
        rows,
        row_bounds=[(12.0, 20.0), (26.0, 34.0), (40.0, 48.0)],
        horizontal_rules=[],
    )

    assert header_rows == [0]
    assert body_rows == [1, 2]


def test_header_detector_does_not_treat_count_row_as_header() -> None:
    """A row starting with n and otherwise containing counts should stay out of the header."""
    rows = [
        ["Characteristics", "Overall", "Non-RA", "RA", "p test"],
        ["n", "5490", "5171", "319", ""],
        ["Gender=Female(%)", "2793(50.9)", "2603(50.3)", "190(59.6)", "0.002"],
    ]

    header_rows, body_rows = detect_header_rows(rows)

    assert header_rows == [0]
    assert body_rows == [1, 2]


def test_fragmented_horizontal_rules_do_not_override_content_fallback() -> None:
    """Weak line evidence should not displace the existing heuristic detector."""
    rows = [
        ["Characteristic", "Overall", "P-value"],
        ["Age, years", "52.1", "0.03"],
        ["Male", "34", "0.10"],
    ]

    header_rows, body_rows = detect_header_rows(
        rows,
        row_bounds=[(12.0, 20.0), (26.0, 34.0), (40.0, 48.0)],
        horizontal_rules=[24.0],
    )

    assert header_rows == [0]
    assert body_rows == [1, 2]


def test_row_signature_generation_keeps_raw_and_normalized_forms() -> None:
    """Row signatures should preserve raw text while deriving normalized first-column features."""
    row_view = build_row_signature(1, ["  <HS", "34", "45%"])

    assert row_view.raw_cells == ["  <HS", "34", "45%"]
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


def test_normalization_marks_flush_left_indentation_as_uninformative() -> None:
    """Nearly uniform body-row label positions should not count as informative indentation."""
    extracted = ExtractedTable(
        table_id="tbl-indent-flat",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=4,
        n_cols=2,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable", bbox=(10.0, 10.0, 40.0, 18.0)),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=1, col_idx=0, text="Race", bbox=(10.0, 20.0, 40.0, 28.0)),
            TableCell(row_idx=1, col_idx=1, text=""),
            TableCell(row_idx=2, col_idx=0, text="White", bbox=(10.5, 30.0, 45.0, 38.0)),
            TableCell(row_idx=2, col_idx=1, text="10"),
            TableCell(row_idx=3, col_idx=0, text="Other", bbox=(10.0, 40.0, 45.0, 48.0)),
            TableCell(row_idx=3, col_idx=1, text="12"),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.metadata["indentation_informative"] is False


def test_row_signature_preserves_raw_text_word_boundaries() -> None:
    """Row signatures should keep the raw string untouched while normalizing separately."""
    row_view = build_row_signature(1, ["High school", "34"])

    assert row_view.raw_cells == ["High school", "34"]
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
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.header_rows == [0]
    assert normalized.body_rows == [1, 2]
    assert normalized.row_views[0].first_cell_normalized == "Age years"
    assert normalized.row_views[1].first_cell_alpha_only == "Male"
    assert normalized.metadata["extraction_backend"] == "pymupdf4llm"


def test_normalization_preserves_table_orientation_metadata() -> None:
    """Normalization should preserve extraction metadata about table orientation."""
    extracted = ExtractedTable(
        table_id="tbl-rotated",
        source_pdf="paper.pdf",
        page_num=9,
        title="Table 2",
        caption="Distribution table",
        n_rows=2,
        n_cols=2,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable"),
            TableCell(row_idx=0, col_idx=1, text="Value"),
            TableCell(row_idx=1, col_idx=0, text="DPHP"),
            TableCell(row_idx=1, col_idx=1, text="0.74"),
        ],
        extraction_backend="pymupdf4llm",
        metadata={
            "table_orientation": "rotated",
            "rotation_source": "pymupdf_line_direction",
            "rotation_direction": "vertical_text_up",
            "rotation_confidence": 0.98,
        },
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.metadata["table_orientation"] == "rotated"
    assert normalized.metadata["rotation_source"] == "pymupdf_line_direction"
    assert normalized.metadata["rotation_direction"] == "vertical_text_up"
    assert normalized.metadata["rotation_confidence"] == 0.98


def test_normalized_table_round_trip_serialization(tmp_path: Path) -> None:
    """Normalized tables should round-trip cleanly through the persisted JSON artifact."""
    extracted = ExtractedTable(
        table_id="tbl-roundtrip",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=3,
        n_cols=3,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable"),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=0, col_idx=2, text="P-value"),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
            TableCell(row_idx=1, col_idx=2, text="0.03"),
            TableCell(row_idx=2, col_idx=0, text="Male"),
            TableCell(row_idx=2, col_idx=1, text="34"),
            TableCell(row_idx=2, col_idx=2, text="0.10"),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)
    output_path = tmp_path / "normalized_tables.json"
    write_normalized_tables(output_path, [normalized])
    loaded = load_normalized_tables(output_path)

    assert loaded[0] == normalized


def test_normalized_table_payload_helper_serializes_models() -> None:
    """The payload helper should produce a list of JSON-friendly normalized-table objects."""
    extracted = ExtractedTable(
        table_id="tbl-payload",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=2,
        n_cols=2,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable"),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
        ],
        extraction_backend="pymupdf4llm",
    )

    payload = normalized_tables_to_payload([normalize_extracted_table(extracted)])

    assert payload[0]["table_id"] == "tbl-payload"
    assert payload[0]["header_rows"] == [0]


def test_normalization_uses_rule_metadata_for_header_boundary_when_available() -> None:
    """Normalization should pass optional row-bound and rule metadata into header detection."""
    extracted = ExtractedTable(
        table_id="tbl-rule-header",
        source_pdf="paper.pdf",
        page_num=1,
        title="Table 1",
        caption="Baseline characteristics",
        n_rows=3,
        n_cols=3,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Characteristic"),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=0, col_idx=2, text="P-value"),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
            TableCell(row_idx=1, col_idx=2, text="0.03"),
            TableCell(row_idx=2, col_idx=0, text="Male"),
            TableCell(row_idx=2, col_idx=1, text="34"),
            TableCell(row_idx=2, col_idx=2, text="0.10"),
        ],
        extraction_backend="pymupdf4llm",
        metadata={
            "row_bounds": [(12.0, 20.0), (26.0, 34.0), (40.0, 48.0)],
            "horizontal_rules": [6.0, 24.0],
        },
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.header_rows == [0]
    assert normalized.body_rows == [1, 2]
    assert normalized.metadata["header_detection"]["source"] == "horizontal_rules"
    assert normalized.metadata["header_detection"]["rule_strength"] == "strong"


def test_normalization_accepts_pymupdf_text_layout_rule_metadata() -> None:
    """Normalization should treat PyMuPDF fallback geometry metadata like other extracted tables."""
    extracted = ExtractedTable(
        table_id="tbl-pymupdf-fallback",
        source_pdf="paper.pdf",
        page_num=1,
        title="Table 1",
        caption="Baseline characteristics",
        n_rows=3,
        n_cols=3,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Characteristic"),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=0, col_idx=2, text="P-value"),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
            TableCell(row_idx=1, col_idx=2, text="0.03"),
            TableCell(row_idx=2, col_idx=0, text="Male"),
            TableCell(row_idx=2, col_idx=1, text="34"),
            TableCell(row_idx=2, col_idx=2, text="0.10"),
        ],
        extraction_backend="pymupdf4llm",
        metadata={
            "layout_source": "pymupdf_text_positions",
            "row_bounds": [(12.0, 20.0), (26.0, 34.0), (40.0, 48.0)],
            "horizontal_rules": [6.0, 24.0],
        },
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.metadata["extraction_backend"] == "pymupdf4llm"
    assert normalized.metadata["header_detection"]["source"] == "horizontal_rules"


def test_mostly_empty_leading_column_gets_removed() -> None:
    """A mostly empty leading edge column should be dropped at the table level."""
    extracted = ExtractedTable(
        table_id="tbl-leading-empty",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=3,
        n_cols=4,
        cells=[
            TableCell(row_idx=0, col_idx=0, text=""),
            TableCell(row_idx=0, col_idx=1, text="Variable"),
            TableCell(row_idx=0, col_idx=2, text="Overall"),
            TableCell(row_idx=0, col_idx=3, text="P-value"),
            TableCell(row_idx=1, col_idx=0, text=""),
            TableCell(row_idx=1, col_idx=1, text="Age, years"),
            TableCell(row_idx=1, col_idx=2, text="52.1"),
            TableCell(row_idx=1, col_idx=3, text="0.03"),
            TableCell(row_idx=2, col_idx=0, text=""),
            TableCell(row_idx=2, col_idx=1, text="Male"),
            TableCell(row_idx=2, col_idx=2, text="34"),
            TableCell(row_idx=2, col_idx=3, text="0.10"),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.n_cols == 3
    assert normalized.metadata["dropped_leading_cols"] == 1
    assert normalized.metadata["cleaned_rows"][0] == ["Variable", "Overall", "P-value"]


def test_noisy_mostly_empty_leading_column_still_gets_removed() -> None:
    """A few stray noninformative first-column values should not block leading-column cleanup."""
    extracted = ExtractedTable(
        table_id="tbl-leading-noisy",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=4,
        n_cols=4,
        cells=[
            TableCell(row_idx=0, col_idx=0, text=""),
            TableCell(row_idx=0, col_idx=1, text="Characteristic"),
            TableCell(row_idx=0, col_idx=2, text="Overall"),
            TableCell(row_idx=0, col_idx=3, text=""),
            TableCell(row_idx=1, col_idx=0, text="."),
            TableCell(row_idx=1, col_idx=1, text="n"),
            TableCell(row_idx=1, col_idx=2, text="5490"),
            TableCell(row_idx=1, col_idx=3, text=""),
            TableCell(row_idx=2, col_idx=0, text="1"),
            TableCell(row_idx=2, col_idx=1, text="Age, years"),
            TableCell(row_idx=2, col_idx=2, text="52.1"),
            TableCell(row_idx=2, col_idx=3, text=""),
            TableCell(row_idx=3, col_idx=0, text=""),
            TableCell(row_idx=3, col_idx=1, text="Male"),
            TableCell(row_idx=3, col_idx=2, text="34"),
            TableCell(row_idx=3, col_idx=3, text=""),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.n_cols == 2
    assert normalized.metadata["dropped_leading_cols"] == 1
    assert normalized.metadata["dropped_trailing_cols"] == 1
    assert normalized.metadata["cleaned_rows"][1] == ["n", "5490"]


def test_meaningful_first_column_is_preserved() -> None:
    """A table with real first-column labels should keep the first column."""
    extracted = ExtractedTable(
        table_id="tbl-keep-leading",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=3,
        n_cols=3,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable"),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=0, col_idx=2, text="P-value"),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
            TableCell(row_idx=1, col_idx=2, text="0.03"),
            TableCell(row_idx=2, col_idx=0, text="Male"),
            TableCell(row_idx=2, col_idx=1, text="34"),
            TableCell(row_idx=2, col_idx=2, text="0.10"),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.n_cols == 3
    assert normalized.metadata["dropped_leading_cols"] == 0
    assert normalized.metadata["cleaned_rows"][1][0] == "Age, years"


def test_trailing_mostly_empty_column_is_removed_conservatively() -> None:
    """A mostly empty trailing edge column should be removed without touching inner empties."""
    extracted = ExtractedTable(
        table_id="tbl-trailing-empty",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=3,
        n_cols=4,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Variable"),
            TableCell(row_idx=0, col_idx=1, text="Overall"),
            TableCell(row_idx=0, col_idx=2, text="P-value"),
            TableCell(row_idx=0, col_idx=3, text=""),
            TableCell(row_idx=1, col_idx=0, text="Age, years"),
            TableCell(row_idx=1, col_idx=1, text="52.1"),
            TableCell(row_idx=1, col_idx=2, text="0.03"),
            TableCell(row_idx=1, col_idx=3, text="."),
            TableCell(row_idx=2, col_idx=0, text="Male"),
            TableCell(row_idx=2, col_idx=1, text="34"),
            TableCell(row_idx=2, col_idx=2, text="0.10"),
            TableCell(row_idx=2, col_idx=3, text=""),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.n_cols == 3
    assert normalized.metadata["dropped_trailing_cols"] == 1
    assert normalized.metadata["cleaned_rows"][1] == ["Age, years", "52.1", "0.03"]


def test_inner_empty_cells_are_preserved_when_edge_columns_are_trimmed() -> None:
    """Empty cells inside the remaining grid should not be removed."""
    extracted = ExtractedTable(
        table_id="tbl-inner-empty",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=3,
        n_cols=5,
        cells=[
            TableCell(row_idx=0, col_idx=0, text=""),
            TableCell(row_idx=0, col_idx=1, text="Variable"),
            TableCell(row_idx=0, col_idx=2, text="Overall"),
            TableCell(row_idx=0, col_idx=3, text="P-value"),
            TableCell(row_idx=0, col_idx=4, text=""),
            TableCell(row_idx=1, col_idx=0, text=""),
            TableCell(row_idx=1, col_idx=1, text="Sex"),
            TableCell(row_idx=1, col_idx=2, text=""),
            TableCell(row_idx=1, col_idx=3, text=""),
            TableCell(row_idx=1, col_idx=4, text=""),
            TableCell(row_idx=2, col_idx=0, text="."),
            TableCell(row_idx=2, col_idx=1, text="Male"),
            TableCell(row_idx=2, col_idx=2, text="34"),
            TableCell(row_idx=2, col_idx=3, text="0.10"),
            TableCell(row_idx=2, col_idx=4, text=""),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.metadata["cleaned_rows"][1] == ["Sex", "", ""]
    assert normalized.metadata["cleaned_rows"][2] == ["Male", "34", "0.10"]


def test_row_and_column_order_are_preserved_after_edge_trimming() -> None:
    """Leading/trailing cleanup should preserve the order of remaining rows and columns."""
    extracted = ExtractedTable(
        table_id="tbl-order",
        source_pdf="paper.pdf",
        page_num=1,
        n_rows=4,
        n_cols=5,
        cells=[
            TableCell(row_idx=0, col_idx=0, text=""),
            TableCell(row_idx=0, col_idx=1, text="A"),
            TableCell(row_idx=0, col_idx=2, text="B"),
            TableCell(row_idx=0, col_idx=3, text="C"),
            TableCell(row_idx=0, col_idx=4, text=""),
            TableCell(row_idx=1, col_idx=0, text=""),
            TableCell(row_idx=1, col_idx=1, text="r1"),
            TableCell(row_idx=1, col_idx=2, text="x"),
            TableCell(row_idx=1, col_idx=3, text="y"),
            TableCell(row_idx=1, col_idx=4, text=""),
            TableCell(row_idx=2, col_idx=0, text="1"),
            TableCell(row_idx=2, col_idx=1, text="r2"),
            TableCell(row_idx=2, col_idx=2, text="m"),
            TableCell(row_idx=2, col_idx=3, text="n"),
            TableCell(row_idx=2, col_idx=4, text="."),
            TableCell(row_idx=3, col_idx=0, text=""),
            TableCell(row_idx=3, col_idx=1, text="r3"),
            TableCell(row_idx=3, col_idx=2, text="p"),
            TableCell(row_idx=3, col_idx=3, text="q"),
            TableCell(row_idx=3, col_idx=4, text=""),
        ],
        extraction_backend="pymupdf4llm",
    )

    normalized = normalize_extracted_table(extracted)

    assert normalized.metadata["cleaned_rows"] == [
        ["A", "B", "C"],
        ["r1", "x", "y"],
        ["r2", "m", "n"],
        ["r3", "p", "q"],
    ]
