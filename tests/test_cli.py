"""CLI tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

from table1_parser import cli
from table1_parser.schemas import PaperSection, TableContext
from table1_parser.schemas import ExtractedTable, TableCell


def _build_extracted_table() -> ExtractedTable:
    return ExtractedTable(
        table_id="tbl-1",
        source_pdf="paper.pdf",
        page_num=1,
        title="Table 1",
        caption="Baseline characteristics",
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


def test_cli_extract_stub_prints_not_implemented(capsys) -> None:
    """The extract command should fail gracefully on a missing PDF."""
    exit_code = cli.main(["extract", "paper.pdf"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error" in captured.out


def test_cli_parse_writes_available_stage_outputs_in_one_pass(tmp_path, monkeypatch, capsys) -> None:
    """The parse command should write available stage outputs from one extraction pass."""
    monkeypatch.chdir(tmp_path)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")
    calls = {"extract": 0}

    class FakeExtractor:
        def extract(self, _: str) -> list[ExtractedTable]:
            calls["extract"] += 1
            return [_build_extracted_table()]

    monkeypatch.setattr(cli, "build_extractor", lambda _: FakeExtractor())
    monkeypatch.setattr(cli, "extract_paper_markdown", lambda _: "# Methods\nExample study population.")
    monkeypatch.setattr(
        cli,
        "parse_markdown_sections",
        lambda _: [PaperSection(section_id="section_0", order=0, heading="Methods", level=1, role_hint="methods_like", content="Example study population.")],
    )
    monkeypatch.setattr(
        cli,
        "build_table_contexts",
        lambda sections, definitions: [
            TableContext(
                table_id=definitions[0].table_id,
                table_index=0,
                table_label="Table 1",
                title=definitions[0].title,
                caption=definitions[0].caption,
                methods_like_section_ids=[sections[0].section_id],
            )
        ],
    )

    exit_code = cli.main(["parse", str(pdf_path)])

    captured = capsys.readouterr()
    extracted_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "extracted_tables.json"
    normalized_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "normalized_tables.json"
    table_definition_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "table_definitions.json"
    paper_markdown_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "paper_markdown.md"
    paper_sections_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "paper_sections.json"
    table_context_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "table_contexts" / "table_0_context.json"

    assert exit_code == 0
    assert calls["extract"] == 1
    assert extracted_path.exists()
    assert normalized_path.exists()
    assert table_definition_path.exists()
    assert paper_markdown_path.exists()
    assert paper_sections_path.exists()
    assert table_context_path.exists()
    assert json.loads(extracted_path.read_text(encoding="utf-8"))[0]["table_id"] == "tbl-1"
    assert json.loads(normalized_path.read_text(encoding="utf-8"))[0]["table_id"] == "tbl-1"
    assert json.loads(table_definition_path.read_text(encoding="utf-8"))[0]["table_id"] == "tbl-1"
    assert paper_markdown_path.read_text(encoding="utf-8") == "# Methods\nExample study population."
    assert json.loads(paper_sections_path.read_text(encoding="utf-8"))[0]["section_id"] == "section_0"
    assert json.loads(table_context_path.read_text(encoding="utf-8"))["table_id"] == "tbl-1"
    assert "Wrote parseTable1.out/papers/paper/extracted_tables.json" in captured.out
    assert "Wrote parseTable1.out/papers/paper/normalized_tables.json" in captured.out
    assert "Wrote parseTable1.out/papers/paper/table_definitions.json" in captured.out
    assert "Wrote parseTable1.out/papers/paper/paper_markdown.md" in captured.out
    assert "Wrote parseTable1.out/papers/paper/paper_sections.json" in captured.out
    assert "Wrote parseTable1.out/papers/paper/table_contexts" in captured.out
    assert "Final parsed tables are not implemented yet." in captured.out


def test_cli_extract_writes_default_output_file(tmp_path, monkeypatch, capsys) -> None:
    """The extract command should write JSON under parseTable1.out/papers/<paper>/ by default."""
    monkeypatch.chdir(tmp_path)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")

    class FakeExtractor:
        def extract(self, _: str) -> list[object]:
            return []

    monkeypatch.setattr(cli, "build_extractor", lambda _: FakeExtractor())

    exit_code = cli.main(["extract", str(pdf_path)])

    captured = capsys.readouterr()
    output_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "extracted_tables.json"
    assert exit_code == 0
    assert "Wrote parseTable1.out/papers/paper/extracted_tables.json" in captured.out
    assert json.loads(output_path.read_text(encoding="utf-8")) == []


def test_cli_extract_stdout_preserves_json_output(tmp_path, monkeypatch, capsys) -> None:
    """The extract command should still support explicit stdout JSON output."""
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")

    class FakeTable:
        def model_dump(self, mode: str = "json") -> dict[str, object]:
            return {"table_id": "tbl-1", "mode": mode}

    class FakeExtractor:
        def extract(self, _: str) -> list[object]:
            return [FakeTable()]

    monkeypatch.setattr(cli, "build_extractor", lambda _: FakeExtractor())

    exit_code = cli.main(["extract", str(pdf_path), "--stdout"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == [{"table_id": "tbl-1", "mode": "json"}]


def test_cli_normalize_writes_default_output_file(tmp_path, monkeypatch, capsys) -> None:
    """The normalize command should write JSON under parseTable1.out/papers/<paper>/ by default."""
    monkeypatch.chdir(tmp_path)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")

    class FakeExtractor:
        def extract(self, _: str) -> list[ExtractedTable]:
            return [_build_extracted_table()]

    monkeypatch.setattr(cli, "build_extractor", lambda _: FakeExtractor())

    exit_code = cli.main(["normalize", str(pdf_path)])

    captured = capsys.readouterr()
    output_path = tmp_path / "parseTable1.out" / "papers" / "paper" / "normalized_tables.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert f"Wrote {Path('parseTable1.out') / 'papers' / 'paper' / 'normalized_tables.json'}" in captured.out
    assert payload[0]["table_id"] == "tbl-1"
    assert payload[0]["header_rows"] == [0]
    assert payload[0]["body_rows"] == [1, 2]


def test_cli_normalize_stdout_preserves_json_output(tmp_path, monkeypatch, capsys) -> None:
    """The normalize command should support explicit stdout JSON output."""
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")

    class FakeExtractor:
        def extract(self, _: str) -> list[ExtractedTable]:
            return [_build_extracted_table()]

    monkeypatch.setattr(cli, "build_extractor", lambda _: FakeExtractor())

    exit_code = cli.main(["normalize", str(pdf_path), "--stdout"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload[0]["table_id"] == "tbl-1"
    assert payload[0]["row_views"][0]["first_cell_normalized"] == "Age years"
