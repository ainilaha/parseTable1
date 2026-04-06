"""Tests for the paper-level variable inventory builder."""

from __future__ import annotations

from table1_parser.context import build_paper_variable_inventory
from table1_parser.schemas import ColumnDefinition, DefinedColumn, DefinedVariable, PaperSection, TableDefinition


def _build_definition() -> TableDefinition:
    return TableDefinition(
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
            ),
            DefinedVariable(
                variable_name="Sex",
                variable_label="Sex",
                variable_type="categorical",
                row_start=2,
                row_end=4,
                confidence=0.85,
            ),
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
                ),
                DefinedColumn(
                    col_idx=2,
                    column_name="DKD",
                    column_label="DKD",
                    inferred_role="group",
                    grouping_variable_hint="DKD status",
                ),
            ],
            confidence=0.88,
        ),
    )


def test_inventory_preserves_text_and_table_provenance() -> None:
    """Candidates should merge conservatively while keeping text and table evidence explicit."""
    sections = [
        PaperSection(
            section_id="section_0",
            order=0,
            heading="Abstract",
            level=1,
            role_hint="abstract_like",
            content="Age, years and Sex were measured at baseline.",
        ),
        PaperSection(
            section_id="section_1",
            order=1,
            heading="Methods",
            level=1,
            role_hint="methods_like",
            content="DKD status was the comparison grouping.",
        ),
    ]

    inventory = build_paper_variable_inventory("paper", sections, [_build_definition()])

    age_candidate = next(candidate for candidate in inventory.candidates if candidate.preferred_label == "Age, years")
    assert "text_based" in age_candidate.source_types
    assert "table_variable_label" in age_candidate.source_types
    assert age_candidate.text_support_count >= 1
    assert age_candidate.table_support_count >= 1
    assert "section_0" in age_candidate.section_ids

    grouping_candidate = next(candidate for candidate in inventory.candidates if candidate.preferred_label == "DKD status")
    assert grouping_candidate.table_ids == ["tbl-1"]
    assert grouping_candidate.section_role_hints == ["methods_like"]


def test_inventory_harvests_title_and_caption_mentions_for_seed_terms() -> None:
    """Title and caption mentions should be preserved when seeded variable labels appear there."""
    inventory = build_paper_variable_inventory(
        "paper",
        sections=[],
        table_definitions=[_build_definition()],
    )

    source_types = [mention.source_type for mention in inventory.mentions if mention.raw_label == "DKD status"]
    assert "table_caption" in source_types
    assert "table_grouping_label" in source_types
