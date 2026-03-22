#!/usr/bin/env python3
"""Usage: python scripts/debug_quality_report.py path/to/file.pdf"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _bootstrap_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_bootstrap_repo_root()

from table1_parser.config import Settings
from table1_parser.diagnostics import build_parse_quality_report
from table1_parser.extract import build_extractor
from table1_parser.extract.pdf_loader import open_pdf
from table1_parser.extract.table_detector import detect_table_candidates
from table1_parser.extract.table_selector import select_top_candidates
from table1_parser.heuristics import classify_rows, detect_column_roles, group_variable_blocks
from table1_parser.normalize import normalize_extracted_table


def main() -> int:
    parser = argparse.ArgumentParser(description="Run parse-quality diagnostics for one PDF.")
    parser.add_argument("pdf_path", help="Path to a PDF file.")
    args = parser.parse_args()

    settings = Settings()
    with open_pdf(args.pdf_path) as pdf:
        candidates = detect_table_candidates(pdf)
    if not candidates:
        print("No tables found.")
        return 0

    selected = select_top_candidates(
        candidates=candidates,
        max_candidates=settings.max_table_candidates,
        confidence_threshold=settings.heuristic_confidence_threshold,
    )
    extractor = build_extractor(settings.default_extraction_backend)
    extracted_tables = extractor.extract(args.pdf_path)
    if not extracted_tables:
        print("No extracted tables found.")
        return 0

    selected_idx = selected[0].table_index if selected else 0
    selected_table = extracted_tables[min(selected_idx, len(extracted_tables) - 1)]
    normalized = normalize_extracted_table(selected_table)
    row_classifications = classify_rows(normalized)
    variable_blocks = group_variable_blocks(normalized, row_classifications)
    column_roles = detect_column_roles(normalized)
    report = build_parse_quality_report(
        normalized,
        row_classifications,
        variable_blocks,
        column_roles,
        extracted_table=selected_table,
        source_identifier=args.pdf_path,
    )

    print("selected table")
    print(
        f"  table_id={selected_table.table_id} page={selected_table.page_num} "
        f"dims={selected_table.n_rows}x{selected_table.n_cols} caption={selected_table.caption!r}"
    )
    print("summary")
    print(f"  timestamp={report.report_timestamp}")
    print(f"  body_rows={report.summary.total_body_rows}")
    print(
        f"  unknown_rows={report.summary.unknown_row_count} "
        f"({report.summary.unknown_row_fraction:.2f})"
    )
    print(f"  variable_blocks={report.summary.variable_block_count}")
    print(
        f"  recognized_value_patterns="
        f"{report.summary.recognized_value_pattern_fraction:.2f}"
    )
    print(
        f"  row_warnings={report.summary.row_warning_count} "
        f"column_warnings={report.summary.column_warning_count}"
    )

    for section_name, items in (
        ("table diagnostics", report.table_diagnostics),
        ("row diagnostics", report.row_diagnostics),
        ("column diagnostics", report.column_diagnostics),
    ):
        print(section_name)
        if not items:
            print("  none")
            continue
        for item in items:
            location = []
            if item.row_idx is not None:
                location.append(f"row={item.row_idx}")
            if item.col_idx is not None:
                location.append(f"col={item.col_idx}")
            suffix = f" [{' '.join(location)}]" if location else ""
            print(f"  {item.severity}: {item.code}{suffix} - {item.message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
