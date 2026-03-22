"""Document-context extraction and retrieval tests."""

from __future__ import annotations

import sys
from types import ModuleType

from table1_parser.context.markdown_extractor import extract_paper_markdown
from table1_parser.context.retrieval import build_table_context
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


def test_parse_markdown_sections_detects_methods_and_results() -> None:
    """Markdown heading parsing should create sections with simple role hints."""
    sections = parse_markdown_sections(
        "# Methods\nStudy population.\n\n## Results\nTable 1 shows baseline characteristics."
    )

    assert [section.heading for section in sections] == ["Methods", "Results"]
    assert [section.role_hint for section in sections] == ["methods_like", "results_like"]


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
        "# Results\nTable 2 shows differences by DKD status."
    )

    context = build_table_context(0, definition, sections)

    assert context.table_label == "Table 2"
    assert context.methods_like_section_ids == ["section_0"]
    assert context.results_like_section_ids == ["section_1"]
    assert any(passage.match_type == "table_reference" for passage in context.passages)
    assert "Age" in context.row_terms
    assert "DKD status" in context.grouping_terms
