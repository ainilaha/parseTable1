"""Focused tests for deterministic TableDefinition assembly."""

from __future__ import annotations

import pytest

from table1_parser.heuristics.table_definition_builder import build_table_definition
from table1_parser.heuristics.table_definition_rows import build_defined_variables
from table1_parser.schemas import NormalizedTable, RowView, TableDefinition
from table1_parser.validation.table_definition import validate_table_definition


def _build_row(
    row_idx: int,
    first_cell_raw: str,
    trailing: list[str],
    indent_level: int | None = None,
) -> RowView:
    """Create a compact RowView for TableDefinition tests."""
    raw_cells = [first_cell_raw, *trailing]
    alpha_only = " ".join("".join(ch if ch.isalpha() or ch.isspace() else " " for ch in first_cell_raw).split())
    return RowView(
        row_idx=row_idx,
        raw_cells=raw_cells,
        first_cell_raw=first_cell_raw,
        first_cell_normalized=first_cell_raw,
        first_cell_alpha_only=alpha_only,
        nonempty_cell_count=sum(bool(cell) for cell in raw_cells),
        numeric_cell_count=sum(any(char.isdigit() for char in cell) for cell in raw_cells),
        has_trailing_values=any(bool(cell) for cell in trailing),
        indent_level=indent_level,
        likely_role=None,
    )


def test_build_table_definition_derives_variables_levels_and_columns() -> None:
    """The deterministic builder should assemble SQL-query-ready row and column semantics."""
    table = NormalizedTable(
        table_id="tbl-def",
        title="Table 1. Baseline characteristics by RA status",
        caption="Baseline characteristics by RA status",
        header_rows=[0],
        body_rows=[1, 2, 3, 4],
        row_views=[
            _build_row(1, "Age, years", ["52.3 (14.1)", "51.2 (13.0)", "0.03"]),
            _build_row(2, "Sex", []),
            _build_row(3, "Male", ["412 (48.2)", "201 (44.0)", ""]),
            _build_row(4, "Female", ["442 (51.8)", "255 (56.0)", ""]),
        ],
        n_rows=5,
        n_cols=4,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall", "RA", "P-value"],
                ["Age, years", "52.3 (14.1)", "51.2 (13.0)", "0.03"],
                ["Sex", "", "", ""],
                ["Male", "412 (48.2)", "201 (44.0)", ""],
                ["Female", "442 (51.8)", "255 (56.0)", ""],
            ]
        },
    )

    definition = build_table_definition(table)

    assert definition.table_id == "tbl-def"
    assert definition.variables[0].variable_name == "Age years"
    assert definition.variables[0].variable_type == "continuous"
    assert definition.variables[0].units_hint == "years"
    assert definition.variables[1].variable_label == "Sex"
    assert definition.variables[1].variable_type == "binary"
    assert [level.level_label for level in definition.variables[1].levels] == ["Male", "Female"]
    assert definition.column_definition.grouping_label == "RA status"
    assert definition.column_definition.group_count == 1
    assert [column.column_label for column in definition.column_definition.columns] == ["Overall", "RA", "P-value"]
    assert [column.inferred_role for column in definition.column_definition.columns] == ["overall", "group", "p_value"]
    assert definition.column_definition.columns[1].group_level_label == "RA"
    assert definition.column_definition.columns[1].group_order == 1
    assert definition.column_definition.columns[2].statistic_subtype == "p_value"


def test_build_table_definition_carries_rotated_layout_note() -> None:
    """Rotated tables should carry a simple note for downstream tooling."""
    table = NormalizedTable(
        table_id="tbl-rotated",
        header_rows=[0],
        body_rows=[1],
        row_views=[_build_row(1, "Age, years", ["52.3 (14.1)", "51.2 (13.0)"])],
        n_rows=2,
        n_cols=3,
        metadata={
            "cleaned_rows": [["Characteristic", "Overall", "Case"], ["Age, years", "52.3 (14.1)", "51.2 (13.0)"]],
            "table_orientation": "rotated",
        },
    )

    definition = build_table_definition(table)

    assert "rotated_table_layout" in definition.notes


def test_build_table_definition_preserves_numeric_threshold_and_range_level_names() -> None:
    """Level names should preserve comparator and range syntax, unlike variable names."""
    table = NormalizedTable(
        table_id="tbl-thresholds",
        header_rows=[0],
        body_rows=[1, 2, 3, 4],
        row_views=[
            _build_row(1, "Protein/creatinine ratio, n (%)", []),
            _build_row(2, "< 1.3", ["12 (10.0)"], indent_level=2),
            _build_row(3, "1.3-1.8", ["25 (20.8)"], indent_level=2),
            _build_row(4, ">1.8", ["83 (69.2)"], indent_level=2),
        ],
        n_rows=5,
        n_cols=2,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall"],
                ["Protein/creatinine ratio, n (%)", ""],
                ["< 1.3", "12 (10.0)"],
                ["1.3-1.8", "25 (20.8)"],
                [">1.8", "83 (69.2)"],
            ]
        },
    )

    definition = build_table_definition(table)

    assert definition.variables[0].variable_name == "Protein creatinine ratio"
    assert [level.level_name for level in definition.variables[0].levels] == ["< 1.3", "1.3-1.8", ">1.8"]
    assert [level.level_label for level in definition.variables[0].levels] == ["< 1.3", "1.3-1.8", ">1.8"]


def test_build_table_definition_preserves_textual_comparator_level_names() -> None:
    """Level names should keep comparator-prefixed textual categories distinct."""
    table = NormalizedTable(
        table_id="tbl-education",
        header_rows=[0],
        body_rows=[1, 2, 3],
        row_views=[
            _build_row(1, "Education, n (%)", []),
            _build_row(2, "<High school", ["15 (12.0)"], indent_level=2),
            _build_row(3, ">High school", ["110 (88.0)"], indent_level=2),
        ],
        n_rows=4,
        n_cols=2,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall"],
                ["Education, n (%)", ""],
                ["<High school", "15 (12.0)"],
                [">High school", "110 (88.0)"],
            ]
        },
    )

    definition = build_table_definition(table)

    assert definition.variables[0].variable_name == "Education"
    assert [level.level_name for level in definition.variables[0].levels] == ["<High school", ">High school"]
    assert [level.level_label for level in definition.variables[0].levels] == ["<High school", ">High school"]


def test_variable_and_level_names_use_different_normalization_rules() -> None:
    """Variable rows and level rows should still normalize differently after inlining."""
    table = NormalizedTable(
        table_id="tbl-name-rules",
        header_rows=[0],
        body_rows=[1, 2, 3],
        row_views=[
            _build_row(1, "Age, years, mean (SD)", ["52.3 (14.1)"]),
            _build_row(2, "Education, n (%)", []),
            _build_row(3, ">High school", ["110 (88.0)"], indent_level=2),
        ],
        n_rows=4,
        n_cols=2,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall"],
                ["Age, years, mean (SD)", "52.3 (14.1)"],
                ["Education, n (%)", ""],
                [">High school", "110 (88.0)"],
            ]
        },
    )

    variables = build_defined_variables(table)

    assert variables[0].variable_name == "Age years"
    assert variables[1].variable_name == "Education"
    assert variables[1].levels[0].level_name == ">High school"


def test_one_row_binary_summary_builds_binary_defined_variable() -> None:
    """Standalone count-percent summary rows should map to binary variables."""
    table = NormalizedTable(
        table_id="tbl-binary-row",
        header_rows=[0],
        body_rows=[1, 2],
        row_views=[
            _build_row(1, "Healthy diet", ["172 (6.7%)", "1597 (76.9%)", "1540 (67.0%)", "<0.001"]),
            _build_row(2, "Age, years", ["36.0 (12.0)", "44.0 (13.0)", "45.0 (14.0)", "<0.001"]),
        ],
        n_rows=3,
        n_cols=5,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Low", "Middle", "High", "P-value"],
                ["Healthy diet", "172 (6.7%)", "1597 (76.9%)", "1540 (67.0%)", "<0.001"],
                ["Age, years", "36.0 (12.0)", "44.0 (13.0)", "45.0 (14.0)", "<0.001"],
            ]
        },
    )

    variables = build_defined_variables(table)

    assert variables[0].variable_label == "Healthy diet"
    assert variables[0].variable_type == "binary"
    assert variables[0].summary_style_hint == "count_pct"
    assert variables[0].levels == []


def test_validate_table_definition_rejects_invalid_level_row() -> None:
    """Validation should reject row references that do not exist in the normalized table."""
    table = NormalizedTable(
        table_id="tbl-bad",
        header_rows=[0],
        body_rows=[1],
        row_views=[_build_row(1, "Age, years", ["52.3 (14.1)"])],
        n_rows=2,
        n_cols=2,
        metadata={"cleaned_rows": [["Characteristic", "Overall"], ["Age, years", "52.3 (14.1)"]]},
    )
    definition = TableDefinition.model_validate(
        {
            "table_id": "tbl-bad",
            "column_definition": {"columns": [{"col_idx": 1, "column_name": "Overall", "column_label": "Overall"}]},
            "variables": [
                {
                    "variable_name": "Sex",
                    "variable_label": "Sex",
                    "row_start": 1,
                    "row_end": 1,
                    "levels": [{"level_name": "Male", "level_label": "Male", "row_idx": 3}],
                }
            ],
        }
    )

    with pytest.raises(ValueError):
        validate_table_definition(definition, table)


def test_build_table_definition_infers_general_grouping_structure_from_multirow_headers() -> None:
    """Grouped columns should carry group levels, ordering, and statistic subtypes."""
    table = NormalizedTable(
        table_id="tbl-cobalt",
        title="Baseline characteristics",
        caption="Participant characteristics",
        header_rows=[0, 1],
        body_rows=[2],
        row_views=[_build_row(2, "Age, years", ["52.3 (14.1)", "50.4 (13.5)", "51.1 (12.8)", "0.03", "0.01"])],
        n_rows=3,
        n_cols=6,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "", "Cobalt quartile", "Cobalt quartile", "", ""],
                ["", "Overall", "Q1", "Q2", "P-value", "P for trend"],
                ["Age, years", "52.3 (14.1)", "50.4 (13.5)", "51.1 (12.8)", "0.03", "0.01"],
            ]
        },
    )

    definition = build_table_definition(table)

    assert definition.column_definition.grouping_label == "Cobalt quartile"
    assert definition.column_definition.grouping_name == "Cobalt quartile"
    assert definition.column_definition.group_count == 2
    assert [column.inferred_role for column in definition.column_definition.columns] == [
        "overall",
        "group",
        "group",
        "p_value",
        "p_value",
    ]
    assert [column.group_level_label for column in definition.column_definition.columns[:3]] == [None, "Q1", "Q2"]
    assert [column.group_order for column in definition.column_definition.columns[:3]] == [None, 1, 2]
    assert definition.column_definition.columns[3].statistic_subtype == "p_value"
    assert definition.column_definition.columns[4].statistic_subtype == "p_trend"


def test_build_table_definition_supports_grouped_levels_without_known_grouping_variable() -> None:
    """Grouped columns should still be represented when the grouping variable is unclear."""
    table = NormalizedTable(
        table_id="tbl-smoking",
        header_rows=[0],
        body_rows=[1],
        row_views=[_build_row(1, "Body mass index, kg/m2", ["26.1 (5.3)", "24.3 (4.9)", "27.8 (5.8)"])],
        n_rows=2,
        n_cols=4,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall", "Never", "Current"],
                ["Body mass index, kg/m2", "26.1 (5.3)", "24.3 (4.9)", "27.8 (5.8)"],
            ]
        },
    )

    definition = build_table_definition(table)

    assert definition.column_definition.grouping_label is None
    assert definition.column_definition.group_count == 2
    assert [column.inferred_role for column in definition.column_definition.columns] == ["overall", "group", "group"]
    assert [column.group_level_label for column in definition.column_definition.columns] == [None, "Never", "Current"]


def test_build_table_definition_uses_label_column_header_as_grouping_fallback() -> None:
    """When grouped columns have distinct upper labels, the label-column header can define the grouping variable."""
    table = NormalizedTable(
        table_id="tbl-cobalt-repaired",
        header_rows=[0, 1],
        body_rows=[2],
        row_views=[_build_row(2, "Age (yrs), mean±SD", ["60.3±12.0", "58.1±11.2", "60.0±11.4", "61.4±11.6", "<.001"])],
        n_rows=3,
        n_cols=7,
        metadata={
            "cleaned_rows": [
                ["", "", "Q1", "Q2", "Q3", "Q4", "P value"],
                ["Cobalt quartiles (mg/l)", "All", "<=0.12", "0.13-0.14", "0.15-0.18", ">=0.19", "P for trend"],
                ["Age (yrs), mean±SD", "60.3±12.0", "58.1±11.2", "60.0±11.4", "61.4±11.6", "61.7±13.2", "<.001"],
            ]
        },
    )

    definition = build_table_definition(table)

    assert definition.column_definition.grouping_label == "Cobalt quartiles (mg/l)"
    assert definition.column_definition.group_count == 4
    assert [column.group_level_label for column in definition.column_definition.columns] == [
        None,
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        None,
    ]
    assert definition.column_definition.columns[-1].statistic_subtype == "p_trend"
