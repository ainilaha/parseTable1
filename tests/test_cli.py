"""CLI tests for the command-line interface."""

from __future__ import annotations

import json

from table1_parser import cli


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
