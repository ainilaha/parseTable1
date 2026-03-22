"""Schema validation and serialization tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from table1_parser.schemas import (
    ColumnDefinition,
    DefinedColumn,
    DefinedLevel,
    DefinedVariable,
    ExtractedTable,
    LLMTableContext,
    LLMTableParseResponse,
    NormalizedTable,
    PaperSection,
    ParsedColumn,
    ParsedLevel,
    ParsedTable,
    ParsedVariable,
    RetrievedPassage,
    RowView,
    TableCell,
    TableContext,
    TableDefinition,
    ValueRecord,
)


def test_extracted_table_creation_and_serialization() -> None:
    """Extracted tables should instantiate and serialize cleanly."""
    table = ExtractedTable(
        table_id="tbl-1",
        source_pdf="paper.pdf",
        page_num=3,
        title="Table 1",
        caption="Baseline characteristics",
        n_rows=2,
        n_cols=2,
        cells=[
            TableCell(row_idx=0, col_idx=0, text="Age", page_num=3),
            TableCell(row_idx=0, col_idx=1, text="52.1 (8.7)", page_num=3),
        ],
        extraction_backend="pymupdf4llm",
        metadata={"journal": "Example"},
    )

    dumped = table.model_dump()

    assert dumped["table_id"] == "tbl-1"
    assert dumped["cells"][0]["text"] == "Age"
    assert dumped["metadata"]["journal"] == "Example"


def test_row_view_and_normalized_table_creation() -> None:
    """Normalized table schemas should accept row summary inputs."""
    row_view = RowView(
        row_idx=1,
        raw_cells=["Sex", "34 (45%)"],
        first_cell_raw="Sex",
        first_cell_normalized="sex",
        first_cell_alpha_only="sex",
        nonempty_cell_count=2,
        numeric_cell_count=1,
        has_trailing_values=True,
        indent_level=0,
        likely_role="variable",
    )
    table = NormalizedTable(
        table_id="tbl-1",
        title="Table 1",
        caption="Baseline characteristics",
        header_rows=[0],
        body_rows=[1],
        row_views=[row_view],
        n_rows=2,
        n_cols=2,
        metadata={"normalized": True},
    )

    assert table.row_views[0].likely_role == "variable"
    assert table.model_dump()["metadata"]["normalized"] is True


def test_parsed_table_creation_and_serialization() -> None:
    """Parsed table schemas should serialize nested objects correctly."""
    parsed = ParsedTable(
        table_id="tbl-1",
        title="Table 1",
        caption="Baseline characteristics",
        variables=[
            ParsedVariable(
                variable_name="sex",
                variable_label="Sex",
                variable_type="categorical",
                row_start=1,
                row_end=2,
                levels=[ParsedLevel(label="Male", row_idx=2)],
                confidence=0.95,
            )
        ],
        columns=[
            ParsedColumn(
                col_idx=1,
                column_name="overall",
                column_label="Overall",
                inferred_role="overall",
                confidence=0.9,
            )
        ],
        values=[
            ValueRecord(
                row_idx=2,
                col_idx=1,
                variable_name="sex",
                level_label="Male",
                column_name="overall",
                raw_value="34 (45%)",
                value_type="count",
                parsed_numeric=34.0,
                parsed_secondary_numeric=45.0,
                confidence=0.92,
            )
        ],
        notes=["Phase 1 schema smoke test"],
        overall_confidence=0.91,
    )

    dumped = parsed.model_dump(mode="json")

    assert dumped["variables"][0]["levels"][0]["label"] == "Male"
    assert dumped["columns"][0]["inferred_role"] == "overall"
    assert dumped["values"][0]["parsed_secondary_numeric"] == 45.0


def test_table_definition_creation_and_serialization() -> None:
    """TableDefinition schemas should serialize nested row and column definitions correctly."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1",
        caption="Baseline characteristics by RA status",
        variables=[
            DefinedVariable(
                variable_name="Sex",
                variable_label="Sex",
                variable_type="binary",
                row_start=2,
                row_end=4,
                levels=[
                    DefinedLevel(level_name="Male", level_label="Male", row_idx=3),
                    DefinedLevel(level_name="Female", level_label="Female", row_idx=4),
                ],
                confidence=0.95,
            )
        ],
        column_definition=ColumnDefinition(
            grouping_label="RA status",
            grouping_name="RA status",
            columns=[
                DefinedColumn(
                    col_idx=1,
                    column_name="Overall",
                    column_label="Overall",
                    inferred_role="overall",
                    grouping_variable_hint="RA status",
                    confidence=0.95,
                )
            ],
            confidence=0.95,
        ),
        notes=["deterministic_baseline"],
        overall_confidence=0.95,
    )

    dumped = definition.model_dump(mode="json")

    assert dumped["variables"][0]["levels"][0]["level_label"] == "Male"
    assert dumped["column_definition"]["columns"][0]["inferred_role"] == "overall"


def test_llm_contract_models_create_without_llm_logic() -> None:
    """LLM contract schemas should remain purely structural in Phase 1."""
    context = LLMTableContext(
        table_id="tbl-1",
        row_views=[
            RowView(
                row_idx=0,
                raw_cells=["Variable", "Overall"],
                first_cell_raw="Variable",
                first_cell_normalized="variable",
                first_cell_alpha_only="variable",
                nonempty_cell_count=2,
                numeric_cell_count=0,
                has_trailing_values=False,
                indent_level=0,
                likely_role="header",
            )
        ],
    )
    response = LLMTableParseResponse(
        table_id="tbl-1",
        referenced_row_indices=[0],
        notes=["Placeholder contract only"],
    )

    assert context.row_views[0].likely_role == "header"
    assert response.model_dump()["referenced_row_indices"] == [0]


def test_document_context_schemas_create_without_llm_logic() -> None:
    """Document-context schemas should serialize cleanly."""
    section = PaperSection(
        section_id="section_0",
        order=0,
        heading="Methods",
        level=1,
        role_hint="methods_like",
        content="Study population and covariates.",
    )
    context = TableContext(
        table_id="tbl-1",
        table_index=0,
        table_label="Table 2",
        title="Table 2",
        caption="Baseline characteristics by DKD status",
        row_terms=["Age"],
        column_terms=["Non-DKD", "DKD"],
        grouping_terms=["DKD status"],
        methods_like_section_ids=["section_0"],
        passages=[
            RetrievedPassage(
                passage_id="section_0_p0",
                section_id="section_0",
                heading="Methods",
                text="Age and DKD status were collected.",
                match_type="methods_term_match",
                score=0.8,
            )
        ],
    )

    assert section.model_dump()["role_hint"] == "methods_like"
    assert context.model_dump(mode="json")["passages"][0]["match_type"] == "methods_term_match"


def test_schema_validation_rejects_invalid_confidence() -> None:
    """Confidence fields should enforce the expected range."""
    with pytest.raises(ValidationError):
        TableCell(row_idx=0, col_idx=0, text="Age", confidence=1.5)
