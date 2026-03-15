"""CLI tests for the Phase 1 scaffold."""

from __future__ import annotations

from table1_parser import cli


def test_cli_extract_stub_prints_not_implemented(capsys) -> None:
    """The extract stub should print the Phase 1 placeholder message."""
    exit_code = cli.main(["extract", "paper.pdf"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert cli.NOT_IMPLEMENTED_MESSAGE in captured.out


def test_cli_parse_stub_prints_not_implemented(capsys) -> None:
    """The parse stub should print the Phase 1 placeholder message."""
    exit_code = cli.main(["parse", "paper.pdf"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert cli.NOT_IMPLEMENTED_MESSAGE in captured.out
