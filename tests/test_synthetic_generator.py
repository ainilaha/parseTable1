from __future__ import annotations

import json
from pathlib import Path

from table1_parser.synthetic import build_truth_json, generate_synthetic_document, load_table_spec, render_html_document
from table1_parser.synthetic.pdf_renderer import _build_pdf_stream, _build_table_layout, _compute_table_top_y


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic_specs"


def test_load_table_spec_validates_example() -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")

    assert spec.document_title == "Synthetic RA baseline document"
    assert spec.columns[0] == "Characteristics"
    assert spec.rows[1].type == "categorical"


def test_render_html_contains_expected_document_text() -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")

    html = render_html_document(spec)

    assert "Synthetic RA baseline document" in html
    assert "Table 1. Baseline characteristics by RA status" in html
    assert "Age (yrs)" in html
    assert "Female" in html
    assert 'id="synthetic-table-spec"' in html


def test_truth_json_contains_variable_blocks_and_row_types() -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")

    truth = build_truth_json(spec)

    assert truth["header_rows"] == [0]
    assert [variable["variable_type"] for variable in truth["variables"]] == ["continuous", "categorical"]
    categorical = truth["variables"][1]
    assert categorical["row_start"] == 1
    assert categorical["row_end"] == 3
    assert [level["label"] for level in categorical["levels"]] == ["Male", "Female"]
    assert [row["row_type"] for row in truth["rows"]] == ["continuous", "categorical_parent", "level", "level"]


def test_layout_options_affect_rendered_output() -> None:
    indented = render_html_document(load_table_spec(EXAMPLES_DIR / "basic_table1.json"))
    flush_left = render_html_document(load_table_spec(EXAMPLES_DIR / "no_indent_table1.json"))

    assert "table--rules" in indented
    assert "padding-left: 1.5rem;" in indented
    assert "padding-left: 1.5rem;" not in flush_left


def test_generator_creates_output_files(tmp_path: Path) -> None:
    outputs = generate_synthetic_document(
        EXAMPLES_DIR / "inline_category_table1.json",
        tmp_path / "inline_category_table1",
    )

    assert set(outputs) == {"html", "pdf", "truth_json"}
    assert outputs["html"].exists()
    assert outputs["truth_json"].exists()
    assert outputs["pdf"].exists()
    assert outputs["pdf"].read_bytes().startswith(b"%PDF-")

    truth = json.loads(outputs["truth_json"].read_text(encoding="utf-8"))
    assert truth["layout_features"]["wrapped_labels"] is True
    assert truth["variables"][0]["variable_label"] == "N"


def test_pdf_rules_follow_finalized_table_row_boundaries() -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")
    layout = _build_table_layout(spec, top_y=_compute_table_top_y(spec))
    stream = _build_pdf_stream(spec)

    header_top = f"{layout.header.top_y:.2f}"
    header_bottom = f"{layout.header.bottom_y:.2f}"
    body_bottom = f"{layout.body_rows[-1].bottom_y:.2f}"

    assert f"{header_top} m 558.00 {header_top} l S" in stream
    assert f"{header_bottom} m 558.00 {header_bottom} l S" in stream
    assert f"{body_bottom} m 558.00 {body_bottom} l S" in stream


def test_wrapped_rows_do_not_use_offset_rule_placement() -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")
    spec.rows[0].label = "Family poverty-income ratio, mean ± SD"
    spec.layout.wrapped_labels = True
    layout = _build_table_layout(spec, top_y=_compute_table_top_y(spec))

    assert layout.body_rows[0].top_y == layout.header.bottom_y
    assert layout.body_rows[0].bottom_y < layout.body_rows[0].top_y
