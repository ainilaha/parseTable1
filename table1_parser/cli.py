"""Command-line interface for the Table 1 parser."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


NOT_IMPLEMENTED_MESSAGE = "Feature not implemented yet"


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="table1-parser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract tables from a PDF.")
    extract_parser.add_argument("pdf_path", help="Path to the source PDF file.")
    extract_parser.set_defaults(handler=_handle_not_implemented)

    parse_parser = subparsers.add_parser("parse", help="Parse a Table 1 PDF.")
    parse_parser.add_argument("pdf_path", help="Path to the source PDF file.")
    parse_parser.set_defaults(handler=_handle_not_implemented)

    return parser


def _handle_not_implemented(_: argparse.Namespace) -> int:
    """Return the Phase 1 placeholder response for unimplemented commands."""
    print(NOT_IMPLEMENTED_MESSAGE)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
