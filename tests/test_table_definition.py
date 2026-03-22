"""Focused tests for deterministic TableDefinition assembly."""

from __future__ import annotations

import pytest

from table1_parser.heuristics.table_definition_builder import build_table_definition
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
    assert [column.column_label for column in definition.column_definition.columns] == ["Overall", "RA", "P-value"]
    assert [column.inferred_role for column in definition.column_definition.columns] == ["overall", "group", "p_value"]


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
