#!/usr/bin/env python3
"""Usage: python scripts/generate_synthetic_table_doc.py spec.json outputs/prefix"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _bootstrap_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_bootstrap_repo_root()

from table1_parser.synthetic import generate_synthetic_document


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic Table 1-style PDF and truth JSON.")
    parser.add_argument("spec_path", help="Path to a synthetic spec JSON file.")
    parser.add_argument("output_prefix", help="Output prefix, for example outputs/basic_table1")
    parser.add_argument("--no-html", action="store_true", help="Skip writing the intermediate HTML file.")
    args = parser.parse_args()

    outputs = generate_synthetic_document(
        args.spec_path,
        args.output_prefix,
        write_html=not args.no_html,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
