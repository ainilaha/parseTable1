from __future__ import annotations

import json
from pathlib import Path

from table1_parser.synthetic import (
    build_truth_json,
    generate_synthetic_document,
    load_table_spec,
    render_html_document,
    render_pdf_from_html,
)
from table1_parser.synthetic.spec_models import expand_display_rows


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic_specs"


def _wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    if not text:
        return [""]
    approx_char_width = font_size * 0.52
    max_chars = max(1, int(max_width / approx_char_width))
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _expected_layout(spec) -> tuple[float, float, float]:
    page_width = 612.0
    page_height = 792.0
    margin_x = 54.0
    margin_y = 54.0
    line_gap = 14.0
    font_size = 11.0

    table_top_y = page_height - margin_y
    table_top_y -= line_gap + 4.0
    if spec.subtitle:
        table_top_y -= len(_wrap_text(spec.subtitle, page_width - (2 * margin_x), font_size)) * line_gap
    for paragraph in spec.paragraphs:
        table_top_y -= len(_wrap_text(paragraph, page_width - (2 * margin_x), font_size)) * line_gap
        table_top_y -= 4.0
    table_top_y -= line_gap + 8.0

    table_width = page_width - (2 * margin_x)
    first_col_width = table_width * 0.40
    other_col_width = (table_width - first_col_width) / max(1, len(spec.columns) - 1)

    def row_bottom(top_y: float, label: str, values: list[str], indent_level: int) -> float:
        cell_padding_y = 5.0
        indent_offset = indent_level * 14.0
        label_lines = _wrap_text(label, max_width=first_col_width - indent_offset, font_size=font_size)
        value_lines = [_wrap_text(value, other_col_width, font_size) for value in values]
        content_lines = max(1, len(label_lines), *(len(lines) for lines in value_lines))
        row_height = (cell_padding_y * 2) + (content_lines * line_gap)
        return top_y - row_height

    header_bottom = row_bottom(table_top_y, spec.columns[0], spec.columns[1:], 0)
    current_top = header_bottom
    last_body_bottom = header_bottom
    for row in expand_display_rows(spec):
        last_body_bottom = row_bottom(current_top, row.label, row.values, row.indent_level)
        current_top = last_body_bottom

    return table_top_y, header_bottom, last_body_bottom


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


def test_pdf_rules_follow_finalized_table_row_boundaries(tmp_path: Path) -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")
    pdf_path = render_pdf_from_html(render_html_document(spec), tmp_path / "basic_table1.pdf")
    pdf_text = pdf_path.read_bytes().decode("latin-1", errors="ignore")
    header_top, header_bottom, body_bottom = _expected_layout(spec)

    assert f"{header_top:.2f} m 558.00 {header_top:.2f} l S" in pdf_text
    assert f"{header_bottom:.2f} m 558.00 {header_bottom:.2f} l S" in pdf_text
    assert f"{body_bottom:.2f} m 558.00 {body_bottom:.2f} l S" in pdf_text


def test_wrapped_rows_do_not_use_offset_rule_placement() -> None:
    spec = load_table_spec(EXAMPLES_DIR / "basic_table1.json")
    spec.rows[0].label = "Family poverty-income ratio, mean ± SD"
    spec.layout.wrapped_labels = True
    _, header_bottom, body_bottom = _expected_layout(spec)

    assert body_bottom < header_bottom
