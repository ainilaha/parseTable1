#!/usr/bin/env python3
"""Usage: python scripts/debug_pipeline.py path/to/file.pdf"""
from __future__ import annotations
import argparse
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
from table1_parser.extract.pdf_loader import open_pdf
from table1_parser.extract.table_detector import detect_table_candidates
from table1_parser.extract.table_selector import select_top_candidates
from table1_parser.heuristics import classify_rows, detect_column_roles, group_variable_blocks
from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.normalize import normalize_extracted_table
def _print_detected_tables(pdf_path: str) -> list[object]:
    with open_pdf(pdf_path) as pdf:
        candidates = detect_table_candidates(pdf)
    print("detected tables")
    if not candidates:
        print("  none")
        return []
    for candidate in candidates:
        dims = f"{len(candidate.raw_rows)}x{max((len(row) for row in candidate.raw_rows), default=0)}"
        label = candidate.caption or "no caption"
        print(f"  idx={candidate.table_index} page={candidate.page_num} dims={dims} caption={label!r}")
    return candidates
def main() -> int:
    parser = argparse.ArgumentParser(description="Debug the current table1_parser pipeline.")
    parser.add_argument("pdf_path", help="Path to a PDF file.")
    args = parser.parse_args()
    settings = Settings()
    try:
        candidates = _print_detected_tables(args.pdf_path)
    except Exception as exc:
        print(f"failed to detect tables: {exc}")
        return 1
    if not candidates:
        print("selected table")
        print("  none")
        return 0
    selected = select_top_candidates(
        candidates=candidates,
        max_candidates=settings.max_table_candidates,
        confidence_threshold=settings.heuristic_confidence_threshold,
    )
    extractor = build_extractor(settings.default_extraction_backend)
    extracted_tables = extractor.extract(args.pdf_path)
    selected_table = extracted_tables[0] if extracted_tables else None
    print("selected table")
    if selected_table is None:
        print("  none")
        return 0
    print(
        f"  idx={selected[0].table_index} page={selected_table.page_num} dims={selected_table.n_rows}x{selected_table.n_cols} "
        f"title={selected_table.title!r} caption={selected_table.caption!r}"
    )
    normalized = normalize_extracted_table(selected_table)
    print("header rows")
    for row_idx in normalized.header_rows:
        row = normalized.metadata.get("cleaned_rows", [])[row_idx]
        print(f"  row {row_idx}: {row}")
    print("first body rows")
    for row_view in normalized.row_views[:5]:
        print(f"  row {row_view.row_idx}: {row_view.raw_cells}")
    try:
        row_classifications = classify_rows(normalized)
        variable_blocks = group_variable_blocks(normalized, row_classifications)
        column_roles = detect_column_roles(normalized)
    except Exception as exc:
        print(f"heuristic stages unavailable: {exc}")
        return 0
    print("row classifications")
    for item in row_classifications:
        print(f"  row {item.row_idx}: {item.classification} ({item.confidence:.2f})")
    print("variable blocks")
    for block in variable_blocks or []:
        print(f"  rows {block.row_start}-{block.row_end}: {block.variable_label!r} [{block.variable_kind}]")
    if not variable_blocks:
        print("  none")
    print("column roles")
    for role in column_roles or []:
        print(f"  col {role.col_idx}: {role.header_label!r} -> {role.role} ({role.confidence:.2f})")
    if not column_roles:
        print("  none")
    print("sample value pattern classifications")
    samples: list[str] = []
    for row_view in normalized.row_views:
        for raw_value in row_view.raw_cells[1:]:
            if raw_value:
                guess = detect_value_pattern(raw_value)
                samples.append(f"  {raw_value!r} -> {guess.pattern} ({guess.confidence:.2f})")
            if len(samples) >= 10:
                break
        if len(samples) >= 10:
            break
    for sample in samples or ["  none"]:
        print(sample)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
