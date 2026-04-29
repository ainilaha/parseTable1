"""Document-context extraction and retrieval tests."""

from __future__ import annotations

import sys
from types import ModuleType

from table1_parser.context import build_paper_variable_inventory
from table1_parser.context.markdown_extractor import extract_paper_markdown
from table1_parser.context.retrieval import build_document_references, build_table_context
from table1_parser.context.section_parser import parse_markdown_sections
from table1_parser.schemas import ColumnDefinition, DefinedColumn, DefinedVariable, TableDefinition


def test_extract_paper_markdown_suppresses_library_stdout(monkeypatch, capsys) -> None:
    """Paper markdown extraction should not leak library stdout."""
    module = ModuleType("pymupdf4llm")

    def _to_markdown(_: str) -> str:
        print("OCR disabled because Tesseract language data not found.")
        return "# Methods\nStudy population"

    module.to_markdown = _to_markdown
    monkeypatch.setitem(sys.modules, "pymupdf4llm", module)

    markdown = extract_paper_markdown("paper.pdf")

    captured = capsys.readouterr()
    assert markdown == "# Methods\nStudy population"
    assert captured.out == ""


def test_extract_paper_markdown_repairs_known_glyph_failures(monkeypatch) -> None:
    """Paper markdown extraction should repair known threshold glyph failures."""
    module = ModuleType("pymupdf4llm")

    def _to_markdown(_: str) -> str:
        return "# Results\n|Q1|�0.12|\n|Q4|≥0.19|\nQ1<br>�0.12"

    module.to_markdown = _to_markdown
    monkeypatch.setitem(sys.modules, "pymupdf4llm", module)

    markdown = extract_paper_markdown("paper.pdf")

    assert "�0.12" not in markdown
    assert "<=0.12" in markdown
    assert "≥0.19" in markdown
    assert "Q1<br><=0.12" in markdown


def test_parse_markdown_sections_detects_methods_and_results() -> None:
    """Markdown heading parsing should create sections with simple role hints."""
    sections = parse_markdown_sections(
        "# Methods\nStudy population.\n\n## Results\nTable 1 shows baseline characteristics."
    )

    assert [section.heading for section in sections] == ["Methods", "Results"]
    assert [section.role_hint for section in sections] == ["methods_like", "results_like"]


def test_parse_markdown_sections_detects_priority_roles_and_references() -> None:
    """Markdown heading parsing should distinguish abstract, discussion, conclusion, and references."""
    sections = parse_markdown_sections(
        "# Abstract\nBackground.\n\n"
        "# Discussion\nMeaning.\n\n"
        "# Conclusions\nTakeaway.\n\n"
        "# References\nAge et al."
    )

    assert [section.role_hint for section in sections] == [
        "abstract_like",
        "discussion_like",
        "conclusion_like",
        "references_like",
    ]


def test_build_table_context_collects_table_mentions_and_term_matches() -> None:
    """Per-table retrieval should preserve table mentions and methods-like evidence."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 2",
        caption="Table 2. Baseline characteristics by DKD status",
        variables=[
            DefinedVariable(
                variable_name="Age",
                variable_label="Age",
                variable_type="continuous",
                row_start=1,
                row_end=1,
            )
        ],
        column_definition=ColumnDefinition(
            grouping_label="DKD status",
            grouping_name="DKD status",
            columns=[
                DefinedColumn(
                    col_idx=1,
                    column_name="Non DKD",
                    column_label="Non-DKD",
                    inferred_role="group",
                ),
                DefinedColumn(
                    col_idx=2,
                    column_name="DKD",
                    column_label="DKD",
                    inferred_role="group",
                ),
            ],
        ),
    )
    sections = parse_markdown_sections(
        "# Study Population\nAge and DKD status were collected.\n\n"
        "# Results\nTable 2 shows differences by DKD status. Figure 1 shows enrollment."
    )

    context = build_table_context(0, definition, sections)

    assert context.table_label == "Table 2"
    assert context.methods_like_section_ids == ["section_0"]
    assert context.results_like_section_ids == ["section_1"]
    assert any(passage.match_type == "table_reference" for passage in context.passages)
    assert any(reference.reference_label == "Table 2" for reference in context.references)
    assert any(
        reference.reference_label == "Figure 1"
        for passage in context.passages
        for reference in passage.references
    )
    assert "Age" in context.row_terms
    assert "DKD status" in context.grouping_terms


def test_build_document_references_collects_table_and_figure_nearby_text() -> None:
    """Reference extraction should keep section and neighboring paragraph context."""
    sections = parse_markdown_sections(
        "# Results\n"
        "Baseline text.\n\n"
        "Table 1 reports baseline characteristics. Fig. 2 shows the flow diagram.\n\n"
        "Follow-up text."
    )

    references = build_document_references(sections)

    assert [reference.reference_label for reference in references] == ["Table 1", "Figure 2"]
    assert references[0].reference_kind == "table"
    assert references[1].reference_kind == "figure"
    assert references[0].section_id == "section_0"
    assert references[0].heading == "Results"
    assert references[0].paragraph_index == 1
    assert references[0].previous_text == "Baseline text."
    assert references[0].next_text == "Follow-up text."


def test_build_paper_variable_inventory_prioritizes_sections_and_excludes_references() -> None:
    """Paper variable inventory should gather table and text mentions without harvesting references."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1",
        caption="Table 1. Baseline characteristics by DKD status",
        variables=[
            DefinedVariable(
                variable_name="Age years",
                variable_label="Age, years",
                variable_type="continuous",
                row_start=1,
                row_end=1,
                confidence=0.9,
            )
        ],
        column_definition=ColumnDefinition(
            grouping_label="DKD status",
            grouping_name="DKD status",
            columns=[
                DefinedColumn(
                    col_idx=1,
                    column_name="Overall",
                    column_label="Overall",
                    inferred_role="overall",
                )
            ],
        ),
    )
    sections = parse_markdown_sections(
        "# Abstract\nAge, years was a primary baseline covariate.\n\n"
        "# Methods\nDKD status and Age, years were assessed at baseline.\n\n"
        "# Results\nTable 1 reports Age, years by DKD status.\n\n"
        "# References\nAge, years in older cohorts."
    )

    inventory = build_paper_variable_inventory("paper", sections, [definition])

    text_mentions = [mention for mention in inventory.mentions if mention.source_type == "text_based"]
    assert any(mention.role_hint == "abstract_like" for mention in text_mentions)
    assert any(mention.role_hint == "methods_like" for mention in text_mentions)
    assert any(mention.role_hint == "results_like" for mention in text_mentions)
    assert all(mention.role_hint != "references_like" for mention in text_mentions)
    assert all(mention.table_id is None for mention in text_mentions)
    assert any(mention.source_type == "table_variable_label" for mention in inventory.mentions)
    assert any(candidate.preferred_label == "Age years" for candidate in inventory.candidates)
