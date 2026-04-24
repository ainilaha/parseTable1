"""Smoke tests for the base-R paper output inspection helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
R_SCRIPT = REPO_ROOT / "R" / "inspect_paper_outputs.R"
R_COMPARE_SCRIPT = REPO_ROOT / "R" / "compare_normalized_rows_to_definition.R"
R_JSON_IO_SCRIPT = REPO_ROOT / "R" / "pt1_json_io.R"
R_OBSERVED_SCRIPT = REPO_ROOT / "R" / "observed_table_one.R"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_variable(
    variable_name: str,
    variable_label: str,
    variable_type: str,
    row_start: int,
    row_end: int,
    *,
    levels: list[dict[str, object]] | None = None,
    confidence: float = 0.9,
) -> dict[str, object]:
    return {
        "variable_name": variable_name,
        "variable_label": variable_label,
        "variable_type": variable_type,
        "row_start": row_start,
        "row_end": row_end,
        "levels": levels or [],
        "confidence": confidence,
    }


def _make_column(
    col_idx: int,
    column_name: str,
    column_label: str,
    inferred_role: str,
    *,
    confidence: float = 0.9,
    grouping_variable_hint: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "col_idx": col_idx,
        "column_name": column_name,
        "column_label": column_label,
        "inferred_role": inferred_role,
        "confidence": confidence,
    }
    if grouping_variable_hint is not None:
        payload["grouping_variable_hint"] = grouping_variable_hint
    return payload


def _make_value(
    row_idx: int,
    col_idx: int,
    variable_name: str,
    column_name: str,
    raw_value: str,
    value_type: str,
    parsed_numeric: float,
    *,
    level_label: str | None = None,
    parsed_secondary_numeric: float | None = None,
    confidence: float = 0.9,
) -> dict[str, object]:
    return {
        "row_idx": row_idx,
        "col_idx": col_idx,
        "variable_name": variable_name,
        "level_label": level_label,
        "column_name": column_name,
        "raw_value": raw_value,
        "value_type": value_type,
        "parsed_numeric": parsed_numeric,
        "parsed_secondary_numeric": parsed_secondary_numeric,
        "confidence": confidence,
    }


def _make_parsed_table(
    table_id: str,
    title: str,
    caption: str,
    *,
    variables: list[dict[str, object]] | None = None,
    columns: list[dict[str, object]] | None = None,
    values: list[dict[str, object]] | None = None,
    notes: list[str] | None = None,
    overall_confidence: float = 0.9,
) -> dict[str, object]:
    return {
        "table_id": table_id,
        "title": title,
        "caption": caption,
        "variables": variables or [],
        "columns": columns or [],
        "values": values or [],
        "notes": notes or [],
        "overall_confidence": overall_confidence,
    }


def _make_processing_attempt(
    stage: str,
    name: str,
    *,
    considered: bool,
    ran: bool,
    succeeded: bool,
    note: str | None = None,
) -> dict[str, object]:
    return {
        "stage": stage,
        "name": name,
        "considered": considered,
        "ran": ran,
        "succeeded": succeeded,
        "note": note,
    }


def _make_processing_status(
    table_id: str,
    *,
    status: str,
    failure_stage: str | None = None,
    failure_reason: str | None = None,
    attempts: list[dict[str, object]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "table_id": table_id,
        "status": status,
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "attempts": attempts or [],
        "notes": notes or [],
    }


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


def _write_sample_paper_outputs(
    paper_dir: Path,
    *,
    include_llm: bool,
    include_processing_status: bool = True,
) -> None:
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
                    "metadata": {"grid_refinement_source": "collapsed_explicit_grid_word_positions"},
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
    _write_json(
        paper_dir / "parsed_tables.json",
        [
            _make_parsed_table(
                "tbl-1",
                "Table 1",
                "Baseline characteristics by DKD status",
                variables=[
                    _make_variable("Age years", "Age, years", "continuous", 1, 1),
                ],
                columns=[
                    _make_column(1, "Overall", "Overall", "overall"),
                    _make_column(2, "DKD", "DKD", "group"),
                ],
                values=[
                    _make_value(1, 1, "Age years", "Overall", "52.1", "continuous_summary", 52.1),
                    _make_value(1, 2, "Age years", "DKD", "49.9", "continuous_summary", 49.9),
                ],
            )
        ],
    )
    if include_processing_status:
        _write_json(
            paper_dir / "table_processing_status.json",
            [
                _make_processing_status(
                    "tbl-1",
                    status="ok",
                    attempts=[
                        _make_processing_attempt(
                            "extraction",
                            "explicit_grid_refinement",
                            considered=True,
                            ran=True,
                            succeeded=True,
                            note="collapsed_explicit_grid_word_positions",
                        ),
                        _make_processing_attempt(
                            "table_definition",
                            "deterministic_definition",
                            considered=True,
                            ran=True,
                            succeeded=True,
                            note="variables=1, usable_columns=2",
                        ),
                        _make_processing_attempt(
                            "parsed_table",
                            "deterministic_value_parse",
                            considered=True,
                            ran=True,
                            succeeded=True,
                            note="values=2",
                        ),
                    ],
                    notes=["descriptive_table_candidate", "table_1_candidate"],
                )
            ],
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
                                "confidence": 0.95,
                                "disagrees_with_deterministic": True,
                            }
                        ],
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
    (paper_dir / "paper_variable_inventory.json").write_text(
        json.dumps(
            {
                "paper_id": "paper",
                "mentions": [
                    {
                        "mention_id": "mention_0",
                        "raw_label": "Age, years",
                        "normalized_label": "Age years",
                        "source_type": "text_based",
                        "section_id": "section_1",
                        "heading": "Results",
                        "role_hint": "results_like",
                        "paragraph_index": 0,
                        "evidence_text": "Table 1 shows baseline characteristics by DKD status.",
                        "priority_weight": 0.65,
                        "confidence": 0.78,
                    },
                    {
                        "mention_id": "mention_1",
                        "raw_label": "DKD status",
                        "normalized_label": "DKD status",
                        "source_type": "table_grouping_label",
                        "table_id": "tbl-1",
                        "table_index": 0,
                        "table_label": "Table 1",
                        "priority_weight": 0.7,
                        "confidence": 0.72,
                    },
                ],
                "candidates": [
                    {
                        "candidate_id": "candidate_0",
                        "preferred_label": "Age, years",
                        "normalized_label": "age years",
                        "alternate_labels": ["Age years"],
                        "supporting_mention_ids": ["mention_0"],
                        "source_types": ["text_based"],
                        "section_ids": ["section_1"],
                        "section_role_hints": ["results_like"],
                        "table_ids": [],
                        "table_indices": [],
                        "text_support_count": 1,
                        "table_support_count": 0,
                        "caption_support_count": 0,
                        "priority_score": 0.65,
                        "confidence": 0.78,
                        "interpretation_status": "uninterpreted",
                    },
                    {
                        "candidate_id": "candidate_1",
                        "preferred_label": "DKD status",
                        "normalized_label": "dkd status",
                        "alternate_labels": [],
                        "supporting_mention_ids": ["mention_1"],
                        "source_types": ["table_grouping_label"],
                        "section_ids": [],
                        "section_role_hints": [],
                        "table_ids": ["tbl-1"],
                        "table_indices": [0],
                        "text_support_count": 0,
                        "table_support_count": 1,
                        "caption_support_count": 0,
                        "priority_score": 0.7,
                        "confidence": 0.72,
                        "interpretation_status": "uninterpreted",
                    },
                ],
            },
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


def _write_sample_llm_semantic_debug_run(paper_dir: Path, run_id: str = "20260324T101500Z") -> None:
    debug_dir = paper_dir / "llm_semantic_debug" / run_id
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / "llm_semantic_monitoring.json").write_text(
        json.dumps(
            {
                "report_timestamp": "2026-03-24T10:15:00Z",
                "llm_disabled": False,
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "items": [
                    {
                        "table_id": "tbl-1",
                        "table_index": 0,
                        "table_family": "descriptive_characteristics",
                        "should_run_llm_semantics": True,
                        "status": "success",
                        "elapsed_seconds": 12.4,
                        "retrieved_passage_count": 3,
                        "deterministic_variable_count": 2,
                        "deterministic_column_count": 3,
                        "prompt_char_count": 1820,
                        "response_char_count": 640,
                    },
                    {
                        "table_id": "tbl-2",
                        "table_index": 1,
                        "table_family": "estimate_results",
                        "should_run_llm_semantics": False,
                        "status": "skipped_not_eligible",
                        "retrieved_passage_count": 0,
                        "deterministic_variable_count": 0,
                        "deterministic_column_count": 0,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_r_inspection_helpers_compare_and_show_part_a_note(tmp_path) -> None:
    """The paper-output inspection helpers should compare semantics and note that Part A omits document evidence."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "outputs" / "papers" / "paper"
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
    assert "row-only" in result.stdout
    assert "Table context for table_index=0" in result.stdout
    assert "LLM evidence for table_index=0" in result.stdout
    assert "does not include document-evidence passage IDs" in result.stdout
    assert "section_1_p0" in result.stdout
    assert "baseline characteristics by DKD status" in result.stdout


def test_r_inspection_loads_and_shows_paper_variable_inventory(tmp_path) -> None:
    """The R helper should expose the paper-level variable inventory as simple row-oriented tables."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "outputs" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=False)

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'x <- load_paper_outputs("{paper_dir}"); '
                'cat(x$paper_variable_inventory$paper_id, "\\n"); '
                f'show_paper_variable_mentions("{paper_dir}", source_type = "text_based"); '
                f'show_paper_variable_candidates("{paper_dir}", min_priority = 0.6)'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "paper" in result.stdout
    assert "Paper variable mentions" in result.stdout
    assert "Paper variable candidates" in result.stdout
    assert "Age, years" in result.stdout
    assert "DKD status" in result.stdout


def test_r_inspection_loads_processing_status_and_summarizes_tables(tmp_path) -> None:
    """The R helper should load parsed/status artifacts and summarize one table's processing outcome."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "status" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=False, include_processing_status=True)

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'x <- load_paper_outputs("{paper_dir}"); '
                'cat(length(x$parsed_tables), "\\n"); '
                'cat(length(x$table_processing_status), "\\n"); '
                f'summarize_table_processing("{paper_dir}")'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Table processing summary" in result.stdout
    assert "successful_attempt_count" in result.stdout
    assert "grid_refinement_source" in result.stdout
    assert "collapsed_explicit_grid_word_positions" in result.stdout
    assert "ok" in result.stdout


def test_r_inspection_shows_failed_table_processing_and_structure_header(tmp_path) -> None:
    """The R helper should surface failure status both in the detail view and the structure header."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "failed" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=False, include_processing_status=True)
    (paper_dir / "table_definitions.json").write_text(
        json.dumps(
            [
                {
                    "table_id": "tbl-1",
                    "title": "Table 1",
                    "caption": "Baseline characteristics by DKD status",
                    "variables": [],
                    "column_definition": {"columns": [], "confidence": 0.4},
                    "notes": ["parse_failed:no_variables_for_descriptive_table"],
                    "overall_confidence": 0.4,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_json(
        paper_dir / "parsed_tables.json",
        [
            _make_parsed_table(
                "tbl-1",
                "Table 1",
                "Baseline characteristics by DKD status",
                notes=["parse_failed:no_variables_for_descriptive_table"],
                overall_confidence=0.2,
            )
        ],
    )
    _write_json(
        paper_dir / "table_processing_status.json",
        [
            _make_processing_status(
                "tbl-1",
                status="failed",
                failure_stage="table_definition",
                failure_reason="no_variables_for_descriptive_table",
                attempts=[
                    _make_processing_attempt(
                        "table_definition",
                        "deterministic_definition",
                        considered=True,
                        ran=True,
                        succeeded=False,
                        note="variables=0, usable_columns=0",
                    )
                ],
                notes=["descriptive_table_candidate", "parse_failed:no_variables_for_descriptive_table"],
            )
        ],
    )

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'show_table_processing("{paper_dir}", table_index = 0L); '
                f'show_table_structure("{paper_dir}", table_index = 0L)'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "status: failed" in result.stdout
    assert "failure_stage: table_definition" in result.stdout
    assert "failure_reason: no_variables_for_descriptive_table" in result.stdout
    assert "processing status: failed" in result.stdout
    assert "[No variables]" in result.stdout


def test_r_inspection_loads_without_processing_status(tmp_path) -> None:
    """Older paper dirs without table_processing_status.json should still load and inspect cleanly."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "legacy" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=False, include_processing_status=False)

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'x <- load_paper_outputs("{paper_dir}"); '
                'cat(is.null(x$table_processing_status), "\\n"); '
                f'show_table_processing("{paper_dir}", table_index = 0L); '
                f'summarize_table_processing("{paper_dir}")'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "TRUE" in result.stdout
    assert "[No table_processing_status record found]" in result.stdout
    assert "Table processing summary" in result.stdout


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
    assert "row-only" in result.stdout
    assert "different" in result.stdout


def test_r_compare_normalized_rows_to_definition_supports_one_based_table_index(tmp_path) -> None:
    """The standalone R helper should compare normalized labels to definition labels for any saved table."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "compare_rows" / "papers" / "paper"
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
                    "caption": "Example one",
                    "n_rows": 3,
                    "n_cols": 2,
                    "cells": [],
                    "extraction_backend": "pymupdf4llm",
                },
                {
                    "table_id": "tbl-2",
                    "source_pdf": "paper.pdf",
                    "page_num": 6,
                    "title": "Table 2",
                    "caption": "Example two",
                    "n_rows": 4,
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
                    "caption": "Example one",
                    "header_rows": [0],
                    "body_rows": [1],
                    "row_views": [
                        {
                            "row_idx": 1,
                            "raw_cells": ["Age, years", "52.1"],
                            "first_cell_raw": "Age, years",
                            "first_cell_normalized": "Age years",
                            "first_cell_alpha_only": "Age years",
                            "nonempty_cell_count": 2,
                            "numeric_cell_count": 1,
                            "has_trailing_values": True,
                            "indent_level": 0,
                            "likely_role": "variable",
                        }
                    ],
                    "n_rows": 3,
                    "n_cols": 2,
                    "metadata": {"cleaned_rows": [["Characteristic", "Overall"], ["Age, years", "52.1"]]},
                },
                {
                    "table_id": "tbl-2",
                    "title": "Table 2",
                    "caption": "Example two",
                    "header_rows": [0],
                    "body_rows": [1, 2, 3],
                    "row_views": [
                        {
                            "row_idx": 1,
                            "raw_cells": ["Body mass index (kg/m2), mean (SD)", "27.5"],
                            "first_cell_raw": "Body mass index (kg/m2), mean (SD)",
                            "first_cell_normalized": "Body mass index kg m2 mean SD",
                            "first_cell_alpha_only": "Body mass index kg m mean SD",
                            "nonempty_cell_count": 2,
                            "numeric_cell_count": 1,
                            "has_trailing_values": True,
                            "indent_level": 0,
                            "likely_role": "variable",
                        },
                        {
                            "row_idx": 2,
                            "raw_cells": ["Smoking status, n (%)", ""],
                            "first_cell_raw": "Smoking status, n (%)",
                            "first_cell_normalized": "Smoking status n",
                            "first_cell_alpha_only": "Smoking status n",
                            "nonempty_cell_count": 1,
                            "numeric_cell_count": 0,
                            "has_trailing_values": False,
                            "indent_level": 0,
                            "likely_role": "variable",
                        },
                        {
                            "row_idx": 3,
                            "raw_cells": ["Current", "14"],
                            "first_cell_raw": "Current",
                            "first_cell_normalized": "Current",
                            "first_cell_alpha_only": "Current",
                            "nonempty_cell_count": 2,
                            "numeric_cell_count": 1,
                            "has_trailing_values": True,
                            "indent_level": 2,
                            "likely_role": "level",
                        },
                    ],
                    "n_rows": 4,
                    "n_cols": 2,
                    "metadata": {
                        "cleaned_rows": [
                            ["Characteristic", "Overall"],
                            ["Body mass index (kg/m2), mean (SD)", "27.5"],
                            ["Smoking status, n (%)", ""],
                            ["Current", "14"],
                        ]
                    },
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
                    "caption": "Example one",
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
                    "column_definition": {"columns": [], "confidence": 0.9},
                    "notes": [],
                    "overall_confidence": 0.9,
                },
                {
                    "table_id": "tbl-2",
                    "title": "Table 2",
                    "caption": "Example two",
                    "variables": [
                        {
                            "variable_name": "Body mass index",
                            "variable_label": "Body mass index (kg/m2), mean (SD)",
                            "variable_type": "continuous",
                            "row_start": 1,
                            "row_end": 1,
                            "levels": [],
                            "confidence": 0.9,
                        },
                        {
                            "variable_name": "Smoking status",
                            "variable_label": "Smoking status, n (%)",
                            "variable_type": "categorical",
                            "row_start": 2,
                            "row_end": 3,
                            "levels": [
                                {
                                    "level_name": "Current",
                                    "level_label": "Current",
                                    "row_idx": 3,
                                    "confidence": 0.9,
                                }
                            ],
                            "confidence": 0.9,
                        },
                    ],
                    "column_definition": {"columns": [], "confidence": 0.9},
                    "notes": [],
                    "overall_confidence": 0.9,
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (paper_dir / "paper_sections.json").write_text("[]", encoding="utf-8")
    (paper_dir / "paper_markdown.md").write_text("", encoding="utf-8")

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_COMPARE_SCRIPT}"); '
                f'cmp <- compare_normalized_rows_to_definition("{paper_dir}", table_index = 2L); '
                'print(cmp)'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Body mass index kg m2 mean SD" in result.stdout
    assert "Body mass index (kg/m2), mean (SD)" in result.stdout
    assert "Body mass index" in result.stdout
    assert "Smoking status n" in result.stdout
    assert "Smoking status" in result.stdout
    assert "Current" in result.stdout


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
    assert "row-only" in result.stdout


def test_r_inspection_summarizes_llm_semantic_debug_run(tmp_path) -> None:
    """The R helper should summarize one timestamped semantic-debug monitoring run."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "debug" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=True)
    _write_sample_llm_semantic_debug_run(paper_dir)

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_SCRIPT}"); '
                f'cat(length(list_llm_semantic_debug_runs("{paper_dir}")), "\\n"); '
                f'summarize_llm_semantic_monitoring("{paper_dir}")'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Semantic LLM monitoring summary" in result.stdout
    assert "gpt-4.1-mini" in result.stdout
    assert "success" in result.stdout
    assert "skipped_not_eligible" in result.stdout


def test_r_observed_table_one_from_paper_dir_includes_processing_status_provenance(tmp_path) -> None:
    """The observed-table helper should carry processing status into provenance and print failed status."""
    if not _r_dependencies_available():
        return

    paper_dir = tmp_path / "observed" / "papers" / "paper"
    _write_sample_paper_outputs(paper_dir, include_llm=False, include_processing_status=True)
    _write_json(
        paper_dir / "table_processing_status.json",
        [
            _make_processing_status(
                "tbl-1",
                status="failed",
                failure_stage="parsed_table",
                failure_reason="no_values_after_parse",
                notes=["parse_failed:no_values_after_parse"],
            )
        ],
    )

    result = subprocess.run(
        [
            "Rscript",
            "-e",
            (
                f'source("{R_JSON_IO_SCRIPT}"); '
                f'source("{R_OBSERVED_SCRIPT}"); '
                f'x <- build_observed_table_one_from_paper_dir("{paper_dir}", table_index = 0L); '
                'print(x); '
                'cat(x$provenance$processing_status, "\\n"); '
                'cat(x$provenance$failure_stage, "\\n"); '
                'cat(x$provenance$failure_reason, "\\n")'
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "processing status: failed" in result.stdout
    assert "failure_stage: parsed_table" in result.stdout
    assert "failure_reason: no_values_after_parse" in result.stdout
