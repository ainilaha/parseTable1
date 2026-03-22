"""Command-line interface for the Table 1 parser."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from table1_parser.config import Settings
from table1_parser.extract import build_extractor
from table1_parser.heuristics.table_definition_builder import build_table_definitions, table_definitions_to_payload
from table1_parser.normalize import normalize_extracted_tables, normalized_tables_to_payload, write_normalized_tables

DEFAULT_OUTPUT_DIR = Path("parseTable1.out")


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="table1-parser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract tables from a PDF.")
    extract_parser.add_argument("pdf_path", help="Path to the source PDF file.")
    extract_parser.add_argument(
        "--outdir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Root output directory. Defaults to parseTable1.out.",
    )
    extract_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print extracted JSON to stdout instead of writing files.",
    )
    extract_parser.set_defaults(handler=_handle_extract)

    normalize_parser = subparsers.add_parser("normalize", help="Normalize extracted tables from a PDF.")
    normalize_parser.add_argument("pdf_path", help="Path to the source PDF file.")
    normalize_parser.add_argument(
        "--outdir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Root output directory. Defaults to parseTable1.out.",
    )
    normalize_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print normalized JSON to stdout instead of writing files.",
    )
    normalize_parser.set_defaults(handler=_handle_normalize)

    parse_parser = subparsers.add_parser("parse", help="Parse a Table 1 PDF.")
    parse_parser.add_argument("pdf_path", help="Path to the source PDF file.")
    parse_parser.add_argument(
        "--outdir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Root output directory. Defaults to parseTable1.out.",
    )
    parse_parser.set_defaults(handler=_handle_parse)

    return parser


def _error_payload(message: str) -> str:
    """Return a consistent JSON error payload for CLI failures."""
    return json.dumps({"tables": [], "error": message}, indent=2)


def _validate_pdf_path(pdf_path: str) -> Path | None:
    """Return the PDF path when it exists, otherwise None."""
    path = Path(pdf_path)
    if path.is_file():
        return path
    print(_error_payload(f"PDF not found: {pdf_path}"))
    return None


def _build_default_extractor():
    """Create the configured extraction backend for the current CLI run."""
    settings = Settings()
    return build_extractor(settings.default_extraction_backend)


def _extract_payload(tables: list[object]) -> list[dict[str, object]]:
    """Serialize extracted tables as JSON-ready dictionaries."""
    return [table.model_dump(mode="json") for table in tables]


def _run_available_parse_stages(pdf_path: str) -> tuple[list[object], list[object], list[object]]:
    """Run the currently implemented parse stages once and return their typed outputs."""
    extractor = _build_default_extractor()
    extracted_tables = extractor.extract(pdf_path)
    normalized_tables = normalize_extracted_tables(extracted_tables)
    table_definitions = build_table_definitions(normalized_tables)
    return extracted_tables, normalized_tables, table_definitions


def _handle_extract(args: argparse.Namespace) -> int:
    """Run the Phase 2 extraction backend and serialize results as JSON."""
    if _validate_pdf_path(args.pdf_path) is None:
        return 1

    extractor = _build_default_extractor()

    try:
        tables = extractor.extract(args.pdf_path)
    except Exception as exc:
        print(_error_payload(str(exc)))
        return 1

    payload = _extract_payload(tables)
    if args.stdout:
        print(json.dumps(payload, indent=2))
        return 0

    output_path = _extract_output_path(args.pdf_path, args.outdir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


def _handle_normalize(args: argparse.Namespace) -> int:
    """Extract and normalize tables from a PDF, then serialize the normalized output."""
    if _validate_pdf_path(args.pdf_path) is None:
        return 1

    try:
        _, normalized_tables, _ = _run_available_parse_stages(args.pdf_path)
    except Exception as exc:
        print(_error_payload(str(exc)))
        return 1

    payload = normalized_tables_to_payload(normalized_tables)
    if args.stdout:
        print(json.dumps(payload, indent=2))
        return 0

    output_path = _normalize_output_path(args.pdf_path, args.outdir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_normalized_tables(output_path, normalized_tables)
    print(f"Wrote {output_path}")
    return 0


def _handle_parse(args: argparse.Namespace) -> int:
    """Run the currently implemented parse pipeline once and write all available artifacts."""
    if _validate_pdf_path(args.pdf_path) is None:
        return 1

    try:
        extracted_tables, normalized_tables, table_definitions = _run_available_parse_stages(args.pdf_path)
    except Exception as exc:
        print(_error_payload(str(exc)))
        return 1

    extract_output_path = _extract_output_path(args.pdf_path, args.outdir)
    normalize_output_path = _normalize_output_path(args.pdf_path, args.outdir)
    table_definition_output_path = _table_definition_output_path(args.pdf_path, args.outdir)
    extract_output_path.parent.mkdir(parents=True, exist_ok=True)

    extract_output_path.write_text(
        json.dumps(_extract_payload(extracted_tables), indent=2),
        encoding="utf-8",
    )
    write_normalized_tables(normalize_output_path, normalized_tables)
    table_definition_output_path.write_text(
        json.dumps(table_definitions_to_payload(table_definitions), indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {extract_output_path}")
    print(f"Wrote {normalize_output_path}")
    print(f"Wrote {table_definition_output_path}")
    print("Final parsed tables are not implemented yet.")
    return 0


def _extract_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default extracted-table JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "extracted_tables.json"


def _normalize_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default normalized-table JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "normalized_tables.json"


def _table_definition_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default table-definition JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "table_definitions.json"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
