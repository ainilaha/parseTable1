#!/usr/bin/env python3
"""Usage: python scripts/debug_llm_trace.py path/to/file.pdf [--response-json response.json]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_repo_venv() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    site_packages = (
        repo_root / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    )
    if site_packages.exists():
        sys.path.insert(0, str(site_packages))


_bootstrap_repo_venv()

from table1_parser.config import Settings
from table1_parser.extract import build_extractor
from table1_parser.llm import (
    LLMConfigurationError,
    LLMProviderError,
    LLMTableParser,
    StaticStructuredLLMClient,
    build_llm_client,
)
from table1_parser.normalize import normalize_extracted_table


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 5 parser and write LLM trace artifacts.")
    parser.add_argument("pdf_path", help="Path to a PDF file.")
    parser.add_argument("--table-index", type=int, default=0, help="Extracted table index to trace.")
    parser.add_argument(
        "--trace-dir",
        help="Directory for trace artifacts. Defaults to trace_output/<pdf_stem>/table_<index>.",
    )
    parser.add_argument(
        "--response-json",
        help="Optional JSON file containing a static LLMTableInterpretation-style response.",
    )
    parser.add_argument(
        "--use-configured-client",
        action="store_true",
        help="Use the provider-backed client configured via environment variables instead of the static stub.",
    )
    args = parser.parse_args()

    extractor = build_extractor("pdfplumber")
    tables = extractor.extract(args.pdf_path)
    if not tables:
        print("No tables found.")
        return 0
    if args.table_index < 0 or args.table_index >= len(tables):
        print(f"Invalid table index {args.table_index}; found {len(tables)} table(s).")
        return 1

    table = tables[args.table_index]
    normalized = normalize_extracted_table(table)
    trace_dir = Path(args.trace_dir) if args.trace_dir else Path("trace_output") / Path(args.pdf_path).stem / f"table_{args.table_index}"
    if args.use_configured_client and args.response_json:
        print("Use either --use-configured-client or --response-json, not both.")
        return 1

    if args.response_json:
        response = json.loads(Path(args.response_json).read_text(encoding="utf-8"))
        client = StaticStructuredLLMClient(response=response)
        response_source = args.response_json
    else:
        if not args.use_configured_client:
            print(
                "No LLM source configured. Use --use-configured-client with the required environment "
                "variables, or pass --response-json for an explicit canned response."
            )
            return 1
        try:
            client = build_llm_client(Settings())
        except LLMConfigurationError as exc:
            print(f"LLM configuration error: {exc}")
            print(
                "Configure LLM_PROVIDER, OPENAI_API_KEY, and OPENAI_MODEL before using "
                "--use-configured-client."
            )
            return 1
        response_source = "configured provider client"

    try:
        result = LLMTableParser(client).parse(
            normalized,
            trace_dir=trace_dir,
        )
    except LLMProviderError as exc:
        print(f"LLM provider error: {exc}")
        return 1
    print(f"table_id={table.table_id}")
    print(f"trace_dir={trace_dir}")
    print(f"response_source={response_source}")
    print(f"variables={len(result.variables)} columns={len(result.columns)} notes={len(result.notes)}")
    print("artifacts:")
    for name in ("heuristics.json", "llm_input.json", "llm_output.json", "final_interpretation.json", "diff.txt"):
        print(f"  {trace_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
