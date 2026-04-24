"""Command-line interface for the Table 1 parser."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from table1_parser.config import Settings
from table1_parser.context import (
    build_table_contexts,
    build_paper_variable_inventory,
    extract_paper_markdown,
    paper_variable_inventory_to_payload,
    paper_sections_to_payload,
    parse_markdown_sections,
)
from table1_parser.extract import build_extractor
from table1_parser.heuristics.table_definition_builder import build_table_definitions, table_definitions_to_payload
from table1_parser.heuristics.table_profile import build_table_profiles, table_profiles_to_payload
from table1_parser.llm import (
    LLMConfigurationError,
    LLMSemanticTableDefinitionParser,
    build_llm_client,
)
from table1_parser.normalize import normalize_extracted_tables, normalized_tables_to_payload, write_normalized_tables
from table1_parser.parse import build_parsed_tables, parsed_tables_to_payload
from table1_parser.processing_status import build_table_processing_statuses
from table1_parser.schemas import LLMSemanticCallRecord, LLMSemanticMonitoringReport

DEFAULT_OUTPUT_DIR = Path("outputs")


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="table1-parser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract tables from a PDF.")
    extract_parser.add_argument("pdf_path", help="Path to the source PDF file.")
    extract_parser.add_argument(
        "--outdir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Root output directory. Defaults to outputs.",
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
        help="Root output directory. Defaults to outputs.",
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
        help="Root output directory. Defaults to outputs.",
    )
    parse_parser.add_argument(
        "--no-llm-semantic",
        action="store_true",
        help="Disable semantic LLM table-definition inference.",
    )
    parse_parser.set_defaults(handler=_handle_parse)

    return parser


def _error_payload(message: str) -> str:
    """Return a consistent JSON error payload for CLI failures."""
    return json.dumps({"tables": [], "error": message}, indent=2)


def _print_stderr(message: str) -> None:
    """Write one diagnostic line to stderr."""
    print(message, file=sys.stderr)


def _validate_pdf_path(pdf_path: str) -> Path | None:
    """Return the PDF path when it exists, otherwise None."""
    path = Path(pdf_path)
    if path.is_file():
        return path
    _print_stderr(_error_payload(f"PDF not found: {pdf_path}"))
    return None


def _build_default_extractor():
    """Create the configured extraction backend for the current CLI run."""
    settings = Settings()
    return build_extractor(settings.default_extraction_backend)


def _extract_payload(tables: list[object]) -> list[dict[str, object]]:
    """Serialize extracted tables as JSON-ready dictionaries."""
    return [table.model_dump(mode="json") for table in tables]


def _handle_extract(args: argparse.Namespace) -> int:
    """Run the Phase 2 extraction backend and serialize results as JSON."""
    if _validate_pdf_path(args.pdf_path) is None:
        return 1

    extractor = _build_default_extractor()

    try:
        tables = extractor.extract(args.pdf_path)
    except Exception as exc:
        _print_stderr(_error_payload(str(exc)))
        return 1

    payload = _extract_payload(tables)
    if args.stdout:
        print(json.dumps(payload, indent=2))
        return 0

    output_path = _extract_output_path(args.pdf_path, args.outdir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


def _handle_normalize(args: argparse.Namespace) -> int:
    """Extract and normalize tables from a PDF, then serialize the normalized output."""
    if _validate_pdf_path(args.pdf_path) is None:
        return 1

    try:
        extractor = _build_default_extractor()
        normalized_tables = normalize_extracted_tables(extractor.extract(args.pdf_path))
    except Exception as exc:
        _print_stderr(_error_payload(str(exc)))
        return 1

    payload = normalized_tables_to_payload(normalized_tables)
    if args.stdout:
        print(json.dumps(payload, indent=2))
        return 0

    output_path = _normalize_output_path(args.pdf_path, args.outdir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_normalized_tables(output_path, normalized_tables)
    return 0


def _handle_parse(args: argparse.Namespace) -> int:
    """Run the currently implemented parse pipeline once and write all available artifacts."""
    if _validate_pdf_path(args.pdf_path) is None:
        return 1

    try:
        extractor = _build_default_extractor()
        extracted_tables = extractor.extract(args.pdf_path)
        normalized_tables = normalize_extracted_tables(extracted_tables)
        table_profiles = build_table_profiles(normalized_tables)
        table_definitions = build_table_definitions(normalized_tables)
        parsed_tables = build_parsed_tables(normalized_tables, table_definitions)
        paper_markdown = extract_paper_markdown(args.pdf_path)
        paper_sections = parse_markdown_sections(paper_markdown)
        paper_variable_inventory = build_paper_variable_inventory(paper_stem := Path(args.pdf_path).stem, paper_sections, table_definitions)
        table_contexts = build_table_contexts(paper_sections, table_definitions)
    except Exception as exc:
        _print_stderr(_error_payload(str(exc)))
        return 1

    settings = Settings()
    llm_debug_dir = (
        Path(args.outdir) / "papers" / paper_stem / "llm_semantic_debug" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if settings.llm_debug
        else None
    )
    monitoring_items: list[LLMSemanticCallRecord] = []
    llm_table_definitions: list[object] | None = None
    if args.no_llm_semantic:
        monitoring_items.extend(
            _skipped_llm_monitoring_record(table, profile, definition, context, status="skipped_disabled")
            for table, profile, definition, context in zip(
                normalized_tables,
                table_profiles,
                table_definitions,
                table_contexts,
                strict=True,
            )
        )
        llm_monitoring_report = _monitoring_report(settings, monitoring_items, disabled=True) if settings.llm_debug else None
    else:
        eligible_items: list[tuple[object, object, object, object]] = []
        for table, profile, definition, context in zip(
            normalized_tables,
            table_profiles,
            table_definitions,
            table_contexts,
            strict=True,
        ):
            if getattr(profile, "should_run_llm_semantics", False):
                eligible_items.append((table, profile, definition, context))
            else:
                monitoring_items.append(
                    _skipped_llm_monitoring_record(
                        table,
                        profile,
                        definition,
                        context,
                        status="skipped_not_eligible",
                    )
                )

        if not eligible_items:
            llm_monitoring_report = _monitoring_report(settings, monitoring_items) if settings.llm_debug else None
        else:
            try:
                client = build_llm_client(settings=settings)
            except LLMConfigurationError as exc:
                monitoring_items.extend(
                    _skipped_llm_monitoring_record(
                        table,
                        profile,
                        definition,
                        context,
                        status="skipped_configuration_error",
                        error_message=str(exc),
                    )
                    for table, profile, definition, context in eligible_items
                )
                _print_stderr(f"LLM semantic interpretation skipped: {exc} Use --no-llm-semantic to suppress this warning.")
                llm_monitoring_report = _monitoring_report(settings, monitoring_items) if settings.llm_debug else None
            else:
                parser = LLMSemanticTableDefinitionParser(client)
                definitions: list[object] = []
                for table, profile, definition, context in eligible_items:
                    trace_dir = llm_debug_dir / f"table_{context.table_index}" if llm_debug_dir is not None else None
                    attempt = parser.parse_with_monitoring(table, definition, context, trace_dir=trace_dir)
                    monitoring_items.append(
                        attempt.monitoring.model_copy(
                            update={
                                "table_family": getattr(profile, "table_family", None),
                                "should_run_llm_semantics": getattr(profile, "should_run_llm_semantics", True),
                            }
                        )
                    )
                    if attempt.result is not None:
                        definitions.append(attempt.result)
                    if attempt.error is not None:
                        _print_stderr(
                            f"LLM semantic interpretation skipped for table_index={context.table_index} "
                            f"(table_id={context.table_id}): {attempt.error}"
                        )
                llm_table_definitions = definitions or None
                llm_monitoring_report = _monitoring_report(settings, monitoring_items) if settings.llm_debug else None

    extract_output_path = _extract_output_path(args.pdf_path, args.outdir)
    normalize_output_path = _normalize_output_path(args.pdf_path, args.outdir)
    table_profile_output_path = Path(args.outdir) / "papers" / paper_stem / "table_profiles.json"
    table_definition_output_path = Path(args.outdir) / "papers" / paper_stem / "table_definitions.json"
    parsed_output_path = Path(args.outdir) / "papers" / paper_stem / "parsed_tables.json"
    processing_status_output_path = Path(args.outdir) / "papers" / paper_stem / "table_processing_status.json"
    llm_table_definition_output_path = Path(args.outdir) / "papers" / paper_stem / "table_definitions_llm.json"
    llm_monitoring_output_path = llm_debug_dir / "llm_semantic_monitoring.json" if llm_debug_dir is not None else None
    paper_markdown_output_path = Path(args.outdir) / "papers" / paper_stem / "paper_markdown.md"
    paper_sections_output_path = Path(args.outdir) / "papers" / paper_stem / "paper_sections.json"
    paper_variable_inventory_output_path = Path(args.outdir) / "papers" / paper_stem / "paper_variable_inventory.json"
    table_context_output_dir = Path(args.outdir) / "papers" / paper_stem / "table_contexts"
    table_processing_statuses = build_table_processing_statuses(
        extracted_tables,
        normalized_tables,
        table_profiles,
        table_definitions,
        parsed_tables,
        monitoring_items,
    )
    status_by_table_id = {status.table_id: status for status in table_processing_statuses}
    table_definitions = [
        definition.model_copy(
            update={
                "notes": (
                    [*definition.notes, f"parse_failed:{status_by_table_id[definition.table_id].failure_reason}"]
                    if status_by_table_id[definition.table_id].status == "failed"
                    and f"parse_failed:{status_by_table_id[definition.table_id].failure_reason}" not in definition.notes
                    else definition.notes
                )
            }
        )
        for definition in table_definitions
    ]
    parsed_tables = [
        parsed_table.model_copy(
            update={
                "notes": (
                    [*parsed_table.notes, f"parse_failed:{status_by_table_id[parsed_table.table_id].failure_reason}"]
                    if status_by_table_id[parsed_table.table_id].status == "failed"
                    and f"parse_failed:{status_by_table_id[parsed_table.table_id].failure_reason}" not in parsed_table.notes
                    else parsed_table.notes
                )
            }
        )
        for parsed_table in parsed_tables
    ]
    extract_output_path.parent.mkdir(parents=True, exist_ok=True)
    table_context_output_dir.mkdir(parents=True, exist_ok=True)

    extract_output_path.write_text(
        json.dumps(_extract_payload(extracted_tables), indent=2),
        encoding="utf-8",
    )
    write_normalized_tables(normalize_output_path, normalized_tables)
    table_profile_output_path.write_text(
        json.dumps(table_profiles_to_payload(table_profiles), indent=2) + "\n",
        encoding="utf-8",
    )
    table_definition_output_path.write_text(
        json.dumps(table_definitions_to_payload(table_definitions), indent=2) + "\n",
        encoding="utf-8",
    )
    parsed_output_path.write_text(
        json.dumps(parsed_tables_to_payload(parsed_tables), indent=2) + "\n",
        encoding="utf-8",
    )
    processing_status_output_path.write_text(
        json.dumps([status.model_dump(mode="json") for status in table_processing_statuses], indent=2) + "\n",
        encoding="utf-8",
    )
    if llm_table_definitions is not None:
        llm_table_definition_output_path.write_text(
            json.dumps([definition.model_dump(mode="json") for definition in llm_table_definitions], indent=2) + "\n",
            encoding="utf-8",
        )
    if llm_monitoring_report is not None and llm_monitoring_output_path is not None:
        llm_monitoring_output_path.parent.mkdir(parents=True, exist_ok=True)
        llm_monitoring_output_path.write_text(
            json.dumps(llm_monitoring_report.model_dump(mode="json", exclude_none=True), indent=2) + "\n",
            encoding="utf-8",
        )
    paper_markdown_output_path.write_text(paper_markdown, encoding="utf-8")
    paper_sections_output_path.write_text(
        json.dumps(paper_sections_to_payload(paper_sections), indent=2) + "\n",
        encoding="utf-8",
    )
    paper_variable_inventory_output_path.write_text(
        json.dumps(paper_variable_inventory_to_payload(paper_variable_inventory), indent=2) + "\n",
        encoding="utf-8",
    )
    for table_context in table_contexts:
        (table_context_output_dir / f"table_{table_context.table_index}_context.json").write_text(
            json.dumps(table_context.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


def _extract_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default extracted-table JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "extracted_tables.json"


def _normalize_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default normalized-table JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "normalized_tables.json"


def _skipped_llm_monitoring_record(
    table: object,
    profile: object,
    definition: object,
    context: object,
    *,
    status: str,
    error_message: str | None = None,
) -> LLMSemanticCallRecord:
    """Build one monitoring record for a table that never reached the provider call."""
    body_rows = getattr(table, "body_rows", []) or []
    header_rows = getattr(table, "header_rows", []) or []
    row_views = getattr(table, "row_views", []) or []
    passages = getattr(context, "passages", []) or []
    variables = getattr(definition, "variables", []) or []
    column_definition = getattr(definition, "column_definition", None)
    columns = getattr(column_definition, "columns", []) if column_definition is not None else []
    return LLMSemanticCallRecord(
        table_id=getattr(table, "table_id"),
        table_index=getattr(context, "table_index"),
        table_family=getattr(profile, "table_family", None),
        should_run_llm_semantics=getattr(profile, "should_run_llm_semantics", False),
        status=status,
        header_row_count=len(header_rows),
        body_row_count=len(body_rows),
        header_cell_count=getattr(table, "n_cols", 0) * len(header_rows),
        body_cell_count=sum(len(getattr(row_view, "raw_cells", [])) for row_view in row_views),
        deterministic_variable_count=len(variables),
        deterministic_column_count=len(columns),
        retrieved_passage_count=len(passages),
        retrieved_context_char_count=sum(len(getattr(passage, "text", "")) for passage in passages),
        error_message=error_message,
    )


def _monitoring_report(
    settings: Settings,
    items: list[LLMSemanticCallRecord],
    *,
    disabled: bool = False,
) -> LLMSemanticMonitoringReport:
    """Build one paper-level semantic-LLM monitoring report."""
    return LLMSemanticMonitoringReport(
        report_timestamp=_utc_timestamp(),
        llm_disabled=disabled,
        provider=settings.llm_provider,
        model=settings.active_llm_model,
        items=items,
    )


def _utc_timestamp() -> str:
    """Return a compact UTC ISO 8601 timestamp with trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
