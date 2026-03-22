"""CLI tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

from table1_parser import cli
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
        extraction_backend="pdfplumber",
    )


def test_cli_extract_stub_prints_not_implemented(capsys) -> None:
    """The extract command should fail gracefully on a missing PDF."""
    exit_code = cli.main(["extract", "paper.pdf"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error" in captured.out


def test_cli_parse_stub_prints_not_implemented(capsys) -> None:
    """The parse stub should still print the placeholder message."""
    exit_code = cli.main(["parse", "paper.pdf"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert cli.NOT_IMPLEMENTED_MESSAGE in captured.out


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
