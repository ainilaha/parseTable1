#!/usr/bin/env python3
"""Run the current extraction, normalization, and heuristic stack on a PDF."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


def _bootstrap_repo_venv() -> None:
    """Use the repo-local virtualenv when available and not already active."""
    repo_root = Path(__file__).resolve().parents[1]
    site_packages = (
        repo_root
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    if site_packages.exists():
        sys.path.insert(0, str(site_packages))


_bootstrap_repo_venv()

from table1_parser.extract import build_extractor
from table1_parser.heuristics.column_role_detector import detect_column_roles
from table1_parser.heuristics.row_classifier import classify_rows
from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.heuristics.variable_grouper import group_variable_blocks
from table1_parser.normalize import normalize_extracted_table


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Debug the current table1_parser pipeline.")
    parser.add_argument("pdf_path", help="Path to the PDF to inspect.")
    return parser


def _print_table_summary(pdf_path: str) -> None:
    extractor = build_extractor("pdfplumber")
    extracted_tables = extractor.extract(pdf_path)

    print(f"PDF: {pdf_path}")
    print(f"Extracted tables: {len(extracted_tables)}")

    for index, extracted_table in enumerate(extracted_tables, start=1):
        normalized_table = normalize_extracted_table(extracted_table)
        row_classifications = classify_rows(normalized_table)
        variable_blocks = group_variable_blocks(normalized_table, row_classifications)
        column_roles = detect_column_roles(normalized_table)

        value_patterns = []
        for row_view in normalized_table.row_views:
            for raw_value in row_view.raw_cells[1:]:
                if raw_value:
                    value_patterns.append(detect_value_pattern(raw_value))
        pattern_counts = Counter(pattern.pattern for pattern in value_patterns)

        print()
        print(f"[Table {index}] {extracted_table.table_id}")
        print(
            f"  extracted: page={extracted_table.page_num} shape={extracted_table.n_rows}x{extracted_table.n_cols}"
        )
        print(
            f"  normalized: headers={normalized_table.header_rows} body={normalized_table.body_rows}"
        )

        print("  row classifications:")
        for item in row_classifications:
            print(f"    row {item.row_idx}: {item.classification} ({item.confidence:.2f})")

        print("  variable blocks:")
        if variable_blocks:
            for block in variable_blocks:
                print(
                    f"    rows {block.row_start}-{block.row_end}: {block.variable_label!r} "
                    f"[{block.variable_kind}] levels={block.level_row_indices}"
                )
        else:
            print("    none")

        print("  column roles:")
        for role in column_roles:
            print(
                f"    col {role.col_idx}: {role.header_label!r} -> {role.role} ({role.confidence:.2f})"
            )

        print("  value patterns:")
        if pattern_counts:
            print(
                "    "
                + ", ".join(f"{pattern}={count}" for pattern, count in sorted(pattern_counts.items()))
            )
            for pattern in value_patterns[:10]:
                print(
                    f"    sample: {pattern.raw_value!r} -> {pattern.pattern} ({pattern.confidence:.2f})"
                )
        else:
            print("    none")


def main() -> int:
    args = _build_parser().parse_args()
    _print_table_summary(args.pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
