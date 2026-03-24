"""Smoke tests for the base-R paper output inspection helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
R_SCRIPT = REPO_ROOT / "R" / "inspect_paper_outputs.R"


def _r_dependencies_available() -> bool:
    if shutil.which("Rscript") is None:
        return False
    result = subprocess.run(
        ["Rscript", "-e", 'quit(status = if (requireNamespace("jsonlite", quietly = TRUE)) 0 else 1)'],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


def _write_sample_paper_outputs(paper_dir: Path, *, include_llm: bool) -> None:
    context_dir = paper_dir / "table_contexts"
    context_dir.mkdir(parents=True)

    (paper_dir / "extracted_tables.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "source_pdf": "paper.pdf",
                    "page_num": 5,
                    "title": "Table 1",
                    "caption": "Baseline characteristics by DKD status",
                    "n_rows": 4,
                    "n_cols": 3,
                    "cells": [],
                    "extraction_backend": "pymupdf4llm",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "normalized_tables.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "title": "Table 1",
                    "caption": "Baseline characteristics by DKD status",
                    "header_rows": [0],
                    "body_rows": [1, 2],
                    "row_views": [],
                    "n_rows": 3,
                    "n_cols": 3,
                    "metadata": {"cleaned_rows": [["Characteristic", "Overall", "DKD"], ["Age, years", "52.1", "49.9"], ["Sex", "", ""]]},
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "table_definitions.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "title": "Table 1",
                    "caption": "Baseline characteristics by DKD status",
                    "variables": [
                        {
                            "variable_name": "Age years",
                            "variable_label": "Age, years",
                            "variable_type": "continuous",
                            "row_start": 1,
                            "row_end": 1,
                            "levels": [],
                            "confidence": 0.9,
                        }
                    ],
                    "column_definition": {
                        "grouping_label": "DKD status",
                        "grouping_name": "DKD status",
                        "columns": [
                            {
                                "col_idx": 1,
                                "column_name": "Overall",
                                "column_label": "Overall",
                                "inferred_role": "overall",
                                "confidence": 0.9,
                            },
                            {
                                "col_idx": 2,
                                "column_name": "DKD",
                                "column_label": "DKD",
                                "inferred_role": "group",
                                "grouping_variable_hint": "DKD status",
                                "confidence": 0.9,
                            },
                        ],
                        "confidence": 0.9,
                    },
                    "notes": [],
                    "overall_confidence": 0.9,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    if include_llm:
        (paper_dir / "table_definitions_llm.json").write_text(
            json.dumps(
                [
                    {
                        "table_id": "tbl-1",
                        "variables": [
                            {
                                "variable_name": "Age years",
                                "variable_label": "Age at baseline",
                                "variable_type": "continuous",
                                "row_start": 1,
                                "row_end": 1,
                                "levels": [],
                                "evidence_passage_ids": ["section_1_p0"],
                                "confidence": 0.95,
                                "disagrees_with_deterministic": True,
                            }
                        ],
                        "column_definition": {
                            "grouping_label": "DKD status",
                            "grouping_name": "DKD status",
                            "columns": [
                                {
                                    "col_idx": 1,
                                    "column_name": "Overall",
                                    "column_label": "Overall",
                                    "inferred_role": "overall",
                                    "evidence_passage_ids": [],
                                    "confidence": 0.9,
                                },
                                {
                                    "col_idx": 2,
                                    "column_name": "DKD",
                                    "column_label": "DKD case status",
                                    "inferred_role": "comparison_group",
                                    "grouping_variable_hint": "DKD status",
                                    "evidence_passage_ids": ["section_1_p0"],
                                    "confidence": 0.95,
                                    "disagrees_with_deterministic": True,
                                },
                            ],
                            "evidence_passage_ids": ["section_1_p0"],
                            "confidence": 0.95,
                        },
                        "notes": [],
                        "overall_confidence": 0.95,
                    }
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
    (paper_dir / "paper_markdown.md").write_text(
        "# Results\nTable 1 shows baseline characteristics by DKD status.\n",
        encoding="utf-8",
    )
    (paper_dir / "paper_sections.json").write_text(
        json.dumps(
            [
                {
                    "section_id": "section_1",
                    "order": 1,
                    "heading": "Results",
                    "level": 1,
                    "role_hint": "results_like",
                    "content": "Table 1 shows baseline characteristics by DKD status.",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (context_dir / "table_0_context.json").write_text(
        json.dumps(
            {
                "table_id": "tbl-1",
                "table_index": 0,
                "table_label": "Table 1",
                "title": "Table 1",
                "caption": "Baseline characteristics by DKD status",
                "row_terms": ["Age, years"],
                "column_terms": ["DKD"],
                "grouping_terms": ["DKD status"],
                "methods_like_section_ids": [],
                "results_like_section_ids": ["section_1"],
                "passages": [
                    {
                        "passage_id": "section_1_p0",
                        "section_id": "section_1",
                        "heading": "Results",
                        "text": "Table 1 shows baseline characteristics by DKD status.",
                        "match_type": "table_reference",
                        "score": 1.0,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_r_inspection_helpers_compare_and_resolve_context(tmp_path) -> None:
    """The paper-output inspection helpers should compare semantics and resolve evidence passages."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "parseTable1.out" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=True)

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'x <- load_paper_outputs("{paper_dir}"); '
                'cat(length(x$table_definitions), "\\n"); '
                f'compare_table_definitions("{paper_dir}", table_index = 0L); '
                f'show_table_context("{paper_dir}", table_index = 0L, match_type = "table_reference"); '
                f'show_llm_evidence("{paper_dir}", table_index = 0L)'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Variables" in result.stdout
    assert "Columns" in result.stdout
    assert "Table context for table_index=0" in result.stdout
    assert "LLM evidence for table_index=0" in result.stdout
    assert "section_1_p0" in result.stdout
    assert "baseline characteristics by DKD status" in result.stdout


def test_r_inspection_helper_compares_two_runs_at_table_definition_stage(tmp_path) -> None:
    """The R helper should compare table-definition variants across two parse runs."""
    if not _r_dependencies_available():
        return

    no_llm_dir = tmp_path / "compare" / "no_llm" / "papers" / "paper"
    with_llm_dir = tmp_path / "compare" / "with_llm" / "papers" / "paper"
    _write_sample_paper_outputs(no_llm_dir, include_llm=False)
    _write_sample_paper_outputs(with_llm_dir, include_llm=True)

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'compare_table_definition_runs("{no_llm_dir}", "{with_llm_dir}", '
                'table_index = 0L, '
                'variant_a = "deterministic", '
                'variant_b = "llm", '
                'label_a = "no_llm", '
                'label_b = "with_llm_llm")'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Left: no_llm (deterministic)" in result.stdout
    assert "Right: with_llm_llm (llm)" in result.stdout
    assert "Age at baseline" in result.stdout
    assert "DKD case status" in result.stdout
    assert "different" in result.stdout


def test_r_inspection_resolves_sparse_llm_definitions_by_table_id(tmp_path) -> None:
    """The R helper should match sparse LLM outputs by table_id after LLM gating."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "sparse" / "papers" / "paper"
    context_dir = paper_dir / "table_contexts"
    context_dir.mkdir(parents=True)

    (paper_dir / "extracted_tables.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "source_pdf": "paper.pdf",
                    "page_num": 5,
                    "title": "Table 1",
                    "caption": "Estimate results",
                    "n_rows": 2,
                    "n_cols": 2,
                    "cells": [],
                    "extraction_backend": "pymupdf4llm",
                },
                {
                    "table_id": "tbl-2",
                    "source_pdf": "paper.pdf",
                    "page_num": 6,
                    "title": "Table 2",
                    "caption": "Baseline characteristics",
                    "n_rows": 2,
                    "n_cols": 2,
                    "cells": [],
                    "extraction_backend": "pymupdf4llm",
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "normalized_tables.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "title": "Table 1",
                    "caption": "Estimate results",
                    "header_rows": [0],
                    "body_rows": [1],
                    "row_views": [],
                    "n_rows": 2,
                    "n_cols": 2,
                    "metadata": {"cleaned_rows": [["Variable", "HR"], ["Proteinuria", "1.2"]]},
                },
                {
                    "table_id": "tbl-2",
                    "title": "Table 2",
                    "caption": "Baseline characteristics",
                    "header_rows": [0],
                    "body_rows": [1],
                    "row_views": [],
                    "n_rows": 2,
                    "n_cols": 2,
                    "metadata": {"cleaned_rows": [["Variable", "Overall"], ["Age", "52.1"]]},
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "table_definitions.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "title": "Table 1",
                    "caption": "Estimate results",
                    "variables": [],
                    "column_definition": {"columns": [], "confidence": 0.9},
                    "notes": [],
                    "overall_confidence": 0.9,
                },
                {
                    "table_id": "tbl-2",
                    "title": "Table 2",
                    "caption": "Baseline characteristics",
                    "variables": [
                        {
                            "variable_name": "Age",
                            "variable_label": "Age",
                            "variable_type": "continuous",
                            "row_start": 1,
                            "row_end": 1,
                            "levels": [],
                            "confidence": 0.9,
                        }
                    ],
                    "column_definition": {
                        "columns": [
                            {
                                "col_idx": 1,
                                "column_name": "Overall",
                                "column_label": "Overall",
                                "inferred_role": "overall",
                                "confidence": 0.9,
                            }
                        ],
                        "confidence": 0.9,
                    },
                    "notes": [],
                    "overall_confidence": 0.9,
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "table_definitions_llm.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-2",
                    "variables": [
                        {
                            "variable_name": "Age",
                            "variable_label": "Age at baseline",
                            "variable_type": "continuous",
                            "row_start": 1,
                            "row_end": 1,
                            "levels": [],
                            "confidence": 0.95,
                            "disagrees_with_deterministic": True,
                        }
                    ],
                    "column_definition": {
                        "columns": [
                            {
                                "col_idx": 1,
                                "column_name": "Overall",
                                "column_label": "Overall cohort",
                                "inferred_role": "overall",
                                "confidence": 0.95,
                                "disagrees_with_deterministic": True,
                            }
                        ],
                        "confidence": 0.95,
                    },
                    "notes": [],
                    "overall_confidence": 0.95,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "paper_markdown.md").write_text("# Results\nExample paper.\n", encoding="utf-8")
    (paper_dir / "paper_sections.json").write_text(
        json.dumps(
            [
                {
                    "section_id": "section_1",
                    "order": 1,
                    "heading": "Results",
                    "level": 1,
                    "role_hint": "results_like",
                    "content": "Example paper.",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (context_dir / "table_0_context.json").write_text(
        json.dumps({"table_id": "tbl-1", "table_index": 0, "passages": []}, indent=2),
        encoding="utf-8",
    )
    (context_dir / "table_1_context.json").write_text(
        json.dumps({"table_id": "tbl-2", "table_index": 1, "passages": []}, indent=2),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'compare_table_definitions("{paper_dir}", table_index = 1L)'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Age at baseline" in result.stdout
    assert "Overall cohort" in result.stdout
