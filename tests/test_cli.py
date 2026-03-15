"""CLI tests for the command-line interface."""

from __future__ import annotations

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
