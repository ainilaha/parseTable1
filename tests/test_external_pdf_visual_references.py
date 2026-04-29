"""Real-PDF smoke tests for visual-reference artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from table1_parser import cli


EXTERNAL_TESTPAPERS_DIR = Path("/Users/robert/Projects/Epiconnector/testpapers")


def test_external_cobaltpaper_writes_resolved_visual_reference_artifacts(tmp_path) -> None:
    """The external cobaltpaper fixture should produce resolved visual-reference artifacts."""
    pdf_path = EXTERNAL_TESTPAPERS_DIR / "papers_from_johnny" / "cobaltpaper.pdf"
    if not pdf_path.exists():
        pytest.skip(f"External test paper not found: {pdf_path}")

    output_dir = tmp_path / "outputs"
    exit_code = cli.main(["parse", str(pdf_path), "--outdir", str(output_dir)])

    paper_dir = output_dir / "papers" / "cobaltpaper"
    visual_inventory_path = paper_dir / "paper_visual_inventory.json"
    references_path = paper_dir / "paper_references.json"
    table_context_path = paper_dir / "table_contexts" / "table_0_context.json"

    assert exit_code == 0
    assert visual_inventory_path.exists()
    assert references_path.exists()
    assert table_context_path.exists()

    visuals = json.loads(visual_inventory_path.read_text(encoding="utf-8"))
    references = json.loads(references_path.read_text(encoding="utf-8"))
    table_context = json.loads(table_context_path.read_text(encoding="utf-8"))
    visual_ids = {visual["visual_id"] for visual in visuals}

    assert "paper_visual:table:1" in visual_ids
    assert any(visual["reference_check_status"] == "referenced_in_text" for visual in visuals)
    assert any(reference["resolution_status"] == "resolved" for reference in references)
    assert all(
        reference["resolved_visual_id"] in visual_ids
        for reference in references
        if reference["resolution_status"] == "resolved"
    )
    assert table_context["reference_ids"]
    assert table_context["resolved_visual_ids"] == ["paper_visual:table:1"]
