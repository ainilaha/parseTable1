"""Command-line interface for the Table 1 parser."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from table1_parser.config import Settings
from table1_parser.context import (
    build_table_contexts,
    extract_paper_markdown,
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


def _run_available_parse_stages(
    pdf_path: str,
) -> tuple[list[object], list[object], list[object], list[object], list[object], str, list[object], list[object]]:
    """Run the currently implemented parse stages once and return their typed outputs."""
    extractor = _build_default_extractor()
    extracted_tables = extractor.extract(pdf_path)
    normalized_tables = normalize_extracted_tables(extracted_tables)
    table_profiles = build_table_profiles(normalized_tables)
    table_definitions = build_table_definitions(normalized_tables)
    parsed_tables = build_parsed_tables(normalized_tables, table_definitions)
    paper_markdown = extract_paper_markdown(pdf_path)
    paper_sections = parse_markdown_sections(paper_markdown)
    table_contexts = build_table_contexts(paper_sections, table_definitions)
    return (
        extracted_tables,
        normalized_tables,
        table_profiles,
        table_definitions,
        parsed_tables,
        paper_markdown,
        paper_sections,
        table_contexts,
    )


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
        extractor = _build_default_extractor()
        normalized_tables = normalize_extracted_tables(extractor.extract(args.pdf_path))
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
        extracted_tables, normalized_tables, table_profiles, table_definitions, parsed_tables, paper_markdown, paper_sections, table_contexts = _run_available_parse_stages(args.pdf_path)
    except Exception as exc:
        print(_error_payload(str(exc)))
        return 1

    llm_table_definitions, llm_monitoring_report, llm_debug_dir = _maybe_run_semantic_llm(
        args.pdf_path,
        args.outdir,
        normalized_tables,
        table_profiles,
        table_definitions,
        table_contexts,
        disabled=args.no_llm_semantic,
    )

    extract_output_path = _extract_output_path(args.pdf_path, args.outdir)
    normalize_output_path = _normalize_output_path(args.pdf_path, args.outdir)
    table_profile_output_path = _table_profile_output_path(args.pdf_path, args.outdir)
    table_definition_output_path = _table_definition_output_path(args.pdf_path, args.outdir)
    parsed_output_path = _parsed_output_path(args.pdf_path, args.outdir)
    llm_table_definition_output_path = _llm_table_definition_output_path(args.pdf_path, args.outdir)
    llm_monitoring_output_path = _llm_semantic_monitoring_output_path(args.pdf_path, args.outdir, llm_debug_dir)
    paper_markdown_output_path = _paper_markdown_output_path(args.pdf_path, args.outdir)
    paper_sections_output_path = _paper_sections_output_path(args.pdf_path, args.outdir)
    table_context_output_dir = _table_context_output_dir(args.pdf_path, args.outdir)
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
    for table_context in table_contexts:
        _table_context_output_path(table_context_output_dir, table_context.table_index).write_text(
            json.dumps(table_context.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Wrote {extract_output_path}")
    print(f"Wrote {normalize_output_path}")
    print(f"Wrote {table_profile_output_path}")
    print(f"Wrote {table_definition_output_path}")
    print(f"Wrote {parsed_output_path}")
    if llm_table_definitions is not None:
        print(f"Wrote {llm_table_definition_output_path}")
    if llm_monitoring_report is not None and llm_monitoring_output_path is not None:
        print(f"Wrote {llm_monitoring_output_path}")
        if llm_debug_dir is not None:
            print(f"Wrote {llm_debug_dir}")
    print(f"Wrote {paper_markdown_output_path}")
    print(f"Wrote {paper_sections_output_path}")
    print(f"Wrote {table_context_output_dir}")
    return 0


def _maybe_run_semantic_llm(
    pdf_path: str,
    outdir: str,
    normalized_tables: list[object],
    table_profiles: list[object],
    table_definitions: list[object],
    table_contexts: list[object],
    *,
    disabled: bool,
) -> tuple[list[object] | None, LLMSemanticMonitoringReport | None, Path | None]:
    """Return semantic LLM table definitions and optional debug monitoring artifacts."""
    settings = Settings()
    debug_run_dir = _llm_semantic_debug_run_dir(pdf_path, outdir) if settings.llm_debug else None
    monitoring_items: list[LLMSemanticCallRecord] = []
    definitions: list[object] = []
    table_items = list(
        zip(
            normalized_tables,
            table_profiles,
            table_definitions,
            table_contexts,
            strict=True,
        )
    )
    if disabled:
        monitoring_items.extend(
            _skipped_llm_monitoring_record(table, profile, definition, context, status="skipped_disabled")
            for table, profile, definition, context in table_items
        )
        return (
            None,
            _monitoring_report(settings, monitoring_items, disabled=True) if settings.llm_debug else None,
            debug_run_dir,
        )

    eligible_items: list[tuple[object, object, object, object]] = []
    for table, profile, definition, context in table_items:
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
        return None, _monitoring_report(settings, monitoring_items) if settings.llm_debug else None, debug_run_dir

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
        print(f"LLM semantic interpretation skipped: {exc} Use --no-llm-semantic to suppress this warning.")
        return None, _monitoring_report(settings, monitoring_items) if settings.llm_debug else None, debug_run_dir

    parser = LLMSemanticTableDefinitionParser(client)
    for table, profile, definition, context in eligible_items:
        trace_dir = debug_run_dir / f"table_{context.table_index}" if debug_run_dir is not None else None
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
            print(
                f"LLM semantic interpretation skipped for table_index={context.table_index} "
                f"(table_id={context.table_id}): {attempt.error}"
            )

    return (
        definitions or None,
        _monitoring_report(settings, monitoring_items) if settings.llm_debug else None,
        debug_run_dir,
    )


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


def _table_profile_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default table-profile JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "table_profiles.json"


def _llm_table_definition_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default semantic-LLM table-definition JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "table_definitions_llm.json"


def _llm_semantic_debug_run_dir(pdf_path: str, outdir: str) -> Path:
    """Return the timestamped semantic-LLM debug directory for one parse run."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "llm_semantic_debug" / _utc_run_id()


def _llm_semantic_monitoring_output_path(pdf_path: str, outdir: str, debug_run_dir: Path | None) -> Path | None:
    """Return the monitoring-summary path when semantic debug output is enabled."""
    if debug_run_dir is None:
        return None
    return debug_run_dir / "llm_semantic_monitoring.json"


def _parsed_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default final parsed-table JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "parsed_tables.json"


def _paper_markdown_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default paper-markdown path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "paper_markdown.md"


def _paper_sections_output_path(pdf_path: str, outdir: str) -> Path:
    """Return the default paper-sections JSON path for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "paper_sections.json"


def _table_context_output_dir(pdf_path: str, outdir: str) -> Path:
    """Return the default per-table context directory for one paper."""
    paper_stem = Path(pdf_path).stem
    return Path(outdir) / "papers" / paper_stem / "table_contexts"


def _table_context_output_path(output_dir: Path, table_index: int) -> Path:
    """Return one per-table context JSON path."""
    return output_dir / f"table_{table_index}_context.json"


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
        model=settings.openai_model or settings.llm_model,
        items=items,
    )


def _utc_timestamp() -> str:
    """Return a compact UTC ISO 8601 timestamp with trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_run_id() -> str:
    """Return a filesystem-safe UTC timestamp for one debug run directory."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
