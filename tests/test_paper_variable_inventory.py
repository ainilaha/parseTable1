"""Tests for the paper-level variable inventory builder."""

from __future__ import annotations

from table1_parser.context import build_paper_variable_inventory
from table1_parser.schemas import (
    ColumnDefinition,
    DefinedColumn,
    DefinedLevel,
    DefinedVariable,
    PaperSection,
    TableDefinition,
)


def test_inventory_consolidates_decorated_variable_labels() -> None:
    """Decorated table labels should promote one canonical variable candidate."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1",
        caption="Table 1. Baseline characteristics by BMI",
        variables=[
            DefinedVariable(
                variable_name="BMI",
                variable_label="BMI group (kg/m2), n (%)",
                variable_type="categorical",
                row_start=1,
                row_end=4,
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
    sections = [
        PaperSection(
            section_id="section_0",
            order=0,
            heading="Abstract",
            level=1,
            role_hint="abstract_like",
            content="BMI was measured at baseline.",
        )
    ]

    inventory = build_paper_variable_inventory("paper", sections, [definition])

    bmi_candidate = next(candidate for candidate in inventory.candidates if candidate.preferred_label == "BMI")
    assert "BMI group (kg/m2), n (%)" in bmi_candidate.alternate_labels
    assert bmi_candidate.canonical_label == "BMI"
    assert bmi_candidate.canonical_label_source == "deterministic_variable_name"
    assert "text_based" in bmi_candidate.source_types
    assert "table_variable_name" in bmi_candidate.source_types


def test_inventory_filters_ranges_and_quintiles_from_candidates() -> None:
    """Range bins and quantile labels should remain mentions but not candidate variables."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1",
        caption="Table 1. Exposure groups",
        variables=[
            DefinedVariable(
                variable_name="BMI",
                variable_label="BMI group (kg/m2), n (%)",
                variable_type="categorical",
                row_start=1,
                row_end=4,
            ),
            DefinedVariable(
                variable_name="25-30",
                variable_label="25-30",
                variable_type="categorical",
                row_start=5,
                row_end=5,
            ),
            DefinedVariable(
                variable_name="Quintile_1",
                variable_label="Quintile_1",
                variable_type="categorical",
                row_start=6,
                row_end=6,
            ),
        ],
        column_definition=ColumnDefinition(columns=[]),
    )
    sections = [
        PaperSection(
            section_id="section_0",
            order=0,
            heading="Methods",
            level=1,
            role_hint="methods_like",
            content="BMI was categorized for analysis.",
        )
    ]

    inventory = build_paper_variable_inventory("paper", sections, [definition])

    candidate_labels = {candidate.preferred_label for candidate in inventory.candidates}
    assert "BMI" in candidate_labels
    assert "25-30" not in candidate_labels
    assert "Quintile_1" not in candidate_labels

    range_mention = next(mention for mention in inventory.mentions if mention.raw_label == "25-30")
    quintile_mention = next(mention for mention in inventory.mentions if mention.raw_label == "Quintile_1")
    assert range_mention.mention_role == "range_bin"
    assert quintile_mention.mention_role == "level"


def test_inventory_treats_male_as_level_when_sex_parent_is_present() -> None:
    """Common categorical values should be demoted to levels when the parent variable is present."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1",
        caption="Table 1. Participant characteristics",
        variables=[
            DefinedVariable(
                variable_name="Sex",
                variable_label="Sex, n (%)",
                variable_type="categorical",
                row_start=1,
                row_end=3,
                levels=[
                    DefinedLevel(level_name="Male", level_label="Male", row_idx=2),
                    DefinedLevel(level_name="Female", level_label="Female", row_idx=3),
                ],
            ),
            DefinedVariable(
                variable_name="Male",
                variable_label="Male",
                variable_type="categorical",
                row_start=4,
                row_end=4,
            ),
        ],
        column_definition=ColumnDefinition(columns=[]),
    )
    sections = [
        PaperSection(
            section_id="section_0",
            order=0,
            heading="Results",
            level=1,
            role_hint="results_like",
            content="Male participants differed from female participants.",
        )
    ]

    inventory = build_paper_variable_inventory("paper", sections, [definition])

    male_mentions = [mention for mention in inventory.mentions if mention.raw_label == "Male"]
    assert male_mentions
    assert all(mention.mention_role == "level" for mention in male_mentions)
    assert all(candidate.preferred_label != "Male" for candidate in inventory.candidates)


def test_inventory_allows_male_as_variable_without_parent_variable() -> None:
    """Common level labels can remain variables when no parent variable anchors them as levels."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1",
        caption="Table 1. Male subgroup analysis",
        variables=[
            DefinedVariable(
                variable_name="Male",
                variable_label="Male",
                variable_type="binary",
                row_start=1,
                row_end=1,
            )
        ],
        column_definition=ColumnDefinition(columns=[]),
    )
    sections = [
        PaperSection(
            section_id="section_0",
            order=0,
            heading="Methods",
            level=1,
            role_hint="methods_like",
            content="Male was analyzed as the subgrouping variable.",
        )
    ]

    inventory = build_paper_variable_inventory("paper", sections, [definition])

    male_candidate = next(candidate for candidate in inventory.candidates if candidate.preferred_label == "Male")
    assert male_candidate.promotion_basis in {"priority_text_plus_variable_name", "priority_text_support", "deterministic_variable_name"}


def test_inventory_harvests_title_and_caption_mentions_for_canonical_terms() -> None:
    """Title and caption mentions should support canonical variables rather than creating decorated duplicates."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 1. BMI and DKD status",
        caption="Table 1. Baseline characteristics by BMI group (kg/m2), n (%)",
        variables=[
            DefinedVariable(
                variable_name="BMI",
                variable_label="BMI group (kg/m2), n (%)",
                variable_type="categorical",
                row_start=1,
                row_end=4,
            )
        ],
        column_definition=ColumnDefinition(
            grouping_label="DKD status",
            grouping_name="DKD status",
            columns=[],
        ),
    )

    inventory = build_paper_variable_inventory("paper", sections=[], table_definitions=[definition])

    caption_mentions = [mention for mention in inventory.mentions if mention.source_type == "table_caption"]
    assert any(mention.canonical_label == "BMI" for mention in caption_mentions)
    assert any(mention.raw_label == "BMI" for mention in caption_mentions)


def test_inventory_filters_adjustment_variable_lists_from_candidates() -> None:
    """Long adjustment-variable lists should remain artifacts instead of promoted variables."""
    definition = TableDefinition(
        table_id="tbl-1",
        title="Table 2",
        caption="Model covariates",
        variables=[
            DefinedVariable(
                variable_name="race sex educational level PIR marital status",
                variable_label="race, sex, educational level, PIR, marital status,",
                variable_type="unknown",
                row_start=1,
                row_end=1,
            )
        ],
        column_definition=ColumnDefinition(columns=[]),
    )
    sections = [
        PaperSection(
            section_id="section_0",
            order=0,
            heading="Methods",
            level=1,
            role_hint="methods_like",
            content="Models adjusted for race, sex, educational level, PIR, and marital status.",
        )
    ]

    inventory = build_paper_variable_inventory("paper", sections, [definition])

    assert all(candidate.preferred_label != "race sex educational level PIR marital status" for candidate in inventory.candidates)
    artifact_mentions = [mention for mention in inventory.mentions if mention.raw_label.startswith("race")]
    assert artifact_mentions
    assert all(mention.mention_role == "artifact" for mention in artifact_mentions)
