"""Tests for paper-level visual inventory and reference resolution."""

from __future__ import annotations

from table1_parser.context.section_parser import parse_markdown_sections
from table1_parser.context.visual_inventory import build_figure_visuals, build_paper_visual_inventory, build_table_visuals
from table1_parser.context.visual_references import (
    annotate_visual_reference_checks,
    collect_paper_visual_references,
    normalize_visual_label,
    section_paragraphs,
)
from table1_parser.schemas import ColumnDefinition, ExtractedTable, PaperVisual, TableCell, TableDefinition


def _extracted_table(table_id: str = "tbl-1", caption: str | None = "Table 1. Baseline") -> ExtractedTable:
    return ExtractedTable(
        table_id=table_id,
        source_pdf="paper.pdf",
        page_num=4,
        title=None,
        caption=caption,
        n_rows=1,
        n_cols=1,
        cells=[TableCell(row_idx=0, col_idx=0, text="Variable")],
        extraction_backend="pymupdf4llm",
    )


def _table_definition(table_id: str = "tbl-1", title: str | None = "Table 1") -> TableDefinition:
    return TableDefinition(
        table_id=table_id,
        title=title,
        caption=None,
        variables=[],
        column_definition=ColumnDefinition(columns=[]),
    )


def test_visual_label_normalization_handles_common_variants() -> None:
    """Visual labels should normalize case, spacing, abbreviation, and suffix variants."""
    assert normalize_visual_label("Table 1") == "table:1"
    assert normalize_visual_label("TABLE1") == "table:1"
    assert normalize_visual_label("Fig. 2") == "figure:2"
    assert normalize_visual_label("Figure 2a") == "figure:2A"
    assert normalize_visual_label("baseline characteristics") is None


def test_build_table_visuals_uses_extracted_caption_and_dedupes() -> None:
    """Table visuals should come from explicit labels and dedupe repeated table numbers."""
    visuals = build_table_visuals(
        [_extracted_table("tbl-1"), _extracted_table("tbl-1b", "Table 1 (continued). Baseline")],
        [_table_definition("tbl-1"), _table_definition("tbl-1b", "Table 1")],
    )

    assert len(visuals) == 1
    assert visuals[0].visual_id == "paper_visual:table:1"
    assert visuals[0].source_table_id == "tbl-1"
    assert "duplicate_source_table_id:tbl-1b" in visuals[0].notes


def test_build_table_visuals_falls_back_to_definition_title() -> None:
    """Table definitions should provide a fallback label when extraction lacks one."""
    visuals = build_table_visuals([_extracted_table(caption=None)], [_table_definition(title="Table 3")])

    assert visuals[0].visual_id == "paper_visual:table:3"
    assert visuals[0].source == "table_extraction"


def test_build_table_visuals_skips_unlabeled_tables() -> None:
    """Unlabeled tables should not get invented visual IDs."""
    visuals = build_table_visuals([_extracted_table(caption=None)], [_table_definition(title=None)])

    assert visuals == []


def test_build_figure_visuals_detects_captions_but_not_prose_mentions() -> None:
    """Figure visuals should be built from caption-like starts only."""
    sections = parse_markdown_sections(
        "# Results\n"
        "As shown in Figure 2, enrollment was sequential.\n\n"
        "Figure 2. Flow diagram for study inclusion.\n\n"
        "Fig. 3 Study timeline."
    )

    visuals = build_figure_visuals(sections)

    assert [visual.visual_id for visual in visuals] == ["paper_visual:figure:2", "paper_visual:figure:3"]
    assert visuals[0].caption == "Figure 2. Flow diagram for study inclusion."


def test_collect_paper_visual_references_resolves_and_preserves_unresolved_mentions() -> None:
    """Reference collection should resolve only references backed by actual paper visuals."""
    sections = parse_markdown_sections(
        "# Results\nTable1 reports baseline data. Figures 2A and 4 summarize flow.\n\n"
        "# References\nSmith reported this in Figure 9."
    )
    visuals = [
        PaperVisual(visual_id="paper_visual:table:1", visual_kind="table", label="Table 1", number="1"),
        PaperVisual(visual_id="paper_visual:figure:2A", visual_kind="figure", label="Figure 2A", number="2A"),
    ]

    references = collect_paper_visual_references(sections, visuals)

    assert [reference.reference_label for reference in references] == [
        "Table 1",
        "Figure 2A",
        "Figure 4",
        "Figure 9",
    ]
    assert references[0].reference_id == "paper_ref:section_0:p0:r0"
    assert references[0].resolution_status == "resolved"
    assert references[1].resolved_visual_id == "paper_visual:figure:2A"
    assert references[2].resolution_status == "unresolved"
    assert references[3].resolution_status == "external_or_bibliographic"


def test_reference_anchors_exclude_embedded_markdown_table_text() -> None:
    """Reference anchors should keep prose before a collapsed table but not the table body."""
    sections = parse_markdown_sections(
        "# Results\n"
        "Baseline characteristics are shown in Table 1. Table 1 Baseline characteristics "
        "|||Q1|Q2| |---|---| |Age|50|60|"
    )
    visuals = [PaperVisual(visual_id="paper_visual:table:1", visual_kind="table", label="Table 1", number="1")]

    references = collect_paper_visual_references(sections, visuals)

    assert [reference.anchor_text for reference in references] == ["Baseline characteristics are shown in Table 1."]
    assert "|" not in references[0].anchor_text


def test_reference_anchor_uses_sentence_window_by_default() -> None:
    """Reference anchors should include the containing sentence plus nearby sentences."""
    sections = parse_markdown_sections(
        "# Results\n"
        "First sentence. Baseline characteristics are shown in Table 1. Follow-up sentence. Fourth sentence."
    )
    visuals = [PaperVisual(visual_id="paper_visual:table:1", visual_kind="table", label="Table 1", number="1")]

    references = collect_paper_visual_references(sections, visuals)

    assert references[0].anchor_text == (
        "First sentence. Baseline characteristics are shown in Table 1. Follow-up sentence."
    )
    assert references[0].start_char == len("First sentence. Baseline characteristics are shown in ")
    assert references[0].end_char == references[0].start_char + len("Table 1")


def test_section_paragraphs_drop_table_only_chunks() -> None:
    """Markdown table chunks should not become retrieved prose context passages."""
    sections = parse_markdown_sections("# Results\nTable 1 Baseline |||Q1|Q2| |---|---| |Age|50|60|")

    assert section_paragraphs(sections[0]) == []


def test_annotate_visual_reference_checks_excludes_self_mentions_and_exempts_supplement() -> None:
    """Visual reference checks should require non-self text references except for supplements."""
    visuals = [
        PaperVisual(visual_id="paper_visual:table:1", visual_kind="table", label="Table 1", number="1"),
        PaperVisual(visual_id="paper_visual:figure:2", visual_kind="figure", label="Figure 2", number="2"),
        PaperVisual(visual_id="paper_visual:figure:S1", visual_kind="figure", label="Figure S1", number="S1"),
    ]
    sections = parse_markdown_sections(
        "# Results\n"
        "The baseline data are shown in Table 1.\n\n"
        "Table 1. Baseline characteristics |---| value.\n\n"
        "Figure 2. Study flow diagram.\n\n"
        "# Supplement\nFigure S1. Supplementary flow diagram."
    )
    references = collect_paper_visual_references(sections, visuals)

    annotated = annotate_visual_reference_checks(visuals, references)
    by_id = {visual.visual_id: visual for visual in annotated}

    assert by_id["paper_visual:table:1"].reference_check_status == "referenced_in_text"
    assert by_id["paper_visual:table:1"].text_reference_ids == ["paper_ref:section_0:p0:r0"]
    assert by_id["paper_visual:figure:2"].reference_check_status == "no_text_reference"
    assert by_id["paper_visual:figure:S1"].reference_check_status == "supplementary_exempt"


def test_build_paper_visual_inventory_combines_tables_and_figures() -> None:
    """The paper inventory should include table visuals and figure captions."""
    sections = parse_markdown_sections("# Results\nFigure 2. Flow diagram.")

    visuals = build_paper_visual_inventory([_extracted_table()], [_table_definition()], sections)

    assert {visual.visual_id for visual in visuals} == {"paper_visual:table:1", "paper_visual:figure:2"}
