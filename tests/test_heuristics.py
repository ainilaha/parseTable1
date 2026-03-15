"""Focused tests for deterministic heuristic parsing."""

from __future__ import annotations

from table1_parser.heuristics.column_role_detector import detect_column_roles
from table1_parser.heuristics.level_detector import is_common_level_label, is_likely_level_row
from table1_parser.heuristics.row_classifier import classify_rows
from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.heuristics.variable_grouper import group_variable_blocks
from table1_parser.schemas import NormalizedTable, RowView


def _build_row(
    row_idx: int,
    first_cell_raw: str,
    trailing: list[str],
) -> RowView:
    """Create a compact RowView for heuristic tests."""
    raw_cells = [first_cell_raw, *trailing]
    return RowView(
        row_idx=row_idx,
        raw_cells=raw_cells,
        first_cell_raw=first_cell_raw,
        first_cell_normalized=first_cell_raw,
        first_cell_alpha_only="".join(ch if ch.isalpha() or ch.isspace() else " " for ch in first_cell_raw).split() and " ".join("".join(ch if ch.isalpha() or ch.isspace() else " " for ch in first_cell_raw).split()) or "",
        nonempty_cell_count=sum(bool(cell) for cell in raw_cells),
        numeric_cell_count=sum(any(char.isdigit() for char in cell) for cell in raw_cells),
        has_trailing_values=any(bool(cell) for cell in trailing),
        indent_level=None,
        likely_role=None,
    )


def test_row_classifier_handles_required_examples() -> None:
    """Row classification should cover continuous rows, parents, levels, and sections."""
    table = NormalizedTable(
        table_id="tbl-heuristics",
        header_rows=[0],
        body_rows=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        row_views=[
            _build_row(1, "Age, years", ["52.3 (14.1)", "51.2 (13.0)"]),
            _build_row(2, "BMI, kg/m2", ["28.4 (6.1)", "27.0 (5.8)"]),
            _build_row(3, "Sex", []),
            _build_row(4, "Male", ["412 (48.2)", "201 (44.0)"]),
            _build_row(5, "Female", ["442 (51.8)", "255 (56.0)"]),
            _build_row(6, "Education", ["0.120"]),
            _build_row(7, "<HS", ["50 (10.2)", "33 (12.1)"]),
            _build_row(8, "High school", ["200 (40.8)", "101 (37.1)"]),
            _build_row(9, ">High school", ["240 (49.0)", "139 (50.8)"]),
        ],
        n_rows=10,
        n_cols=3,
    )

    classifications = {item.row_idx: item.classification for item in classify_rows(table)}

    assert classifications[1] == "continuous_variable_row"
    assert classifications[2] == "continuous_variable_row"
    assert classifications[3] == "variable_header"
    assert classifications[4] == "level_row"
    assert classifications[5] == "level_row"
    assert classifications[6] == "variable_header"
    assert classifications[7] == "level_row"
    assert classifications[8] == "level_row"
    assert classifications[9] == "level_row"


def test_row_classifier_keeps_negative_cases_unknown_or_section_header() -> None:
    """Negative examples should not be forced into variable or level classes."""
    table = NormalizedTable(
        table_id="tbl-negative",
        header_rows=[0],
        body_rows=[1, 2],
        row_views=[
            _build_row(1, "Baseline characteristics", []),
            _build_row(2, "Random note", ["see text"]),
        ],
        n_rows=3,
        n_cols=2,
    )

    classifications = {item.row_idx: item.classification for item in classify_rows(table)}

    assert classifications[1] == "section_header"
    assert classifications[2] == "unknown"


def test_level_detector_required_examples() -> None:
    """Common categorical levels should be detected conservatively."""
    assert is_common_level_label("Male") is True
    assert is_common_level_label("Female") is True
    assert is_common_level_label("<HS") is True
    assert is_common_level_label("High school") is True
    assert is_common_level_label(">High school") is True
    assert is_common_level_label("Never") is True
    assert is_common_level_label("Former") is True
    assert is_common_level_label("Current") is True
    assert is_common_level_label("Age, years") is False
    assert is_common_level_label("BMI, kg/m2") is False

    assert is_likely_level_row(_build_row(1, "Current", ["50 (20.1)"])) is True
    assert is_likely_level_row(_build_row(2, "Age, years", ["52.3 (14.1)"])) is False


def test_variable_grouper_builds_continuous_and_categorical_blocks() -> None:
    """Grouping should support one-line continuous rows and parent-plus-level blocks."""
    table = NormalizedTable(
        table_id="tbl-grouping",
        header_rows=[0],
        body_rows=[1, 2, 3, 4, 5, 6, 7],
        row_views=[
            _build_row(1, "Age, years", ["52.3 (14.1)", "51.2 (13.0)"]),
            _build_row(2, "Sex", []),
            _build_row(3, "Male", ["412 (48.2)", "201 (44.0)"]),
            _build_row(4, "Female", ["442 (51.8)", "255 (56.0)"]),
            _build_row(5, "Smoking status", []),
            _build_row(6, "Never", ["150 (30.0)", "80 (32.0)"]),
            _build_row(7, "Former", ["100 (20.0)", "40 (16.0)"]),
        ],
        n_rows=8,
        n_cols=3,
    )

    blocks = group_variable_blocks(table)

    assert len(blocks) == 3
    assert blocks[0].variable_label == "Age, years"
    assert blocks[0].variable_kind == "continuous"
    assert blocks[1].variable_label == "Sex"
    assert blocks[1].level_row_indices == [3, 4]
    assert blocks[2].variable_label == "Smoking status"
    assert blocks[2].level_row_indices == [6, 7]


def test_column_role_detector_handles_required_headers() -> None:
    """Column-role detection should classify supported role labels conservatively."""
    table = NormalizedTable(
        table_id="tbl-columns",
        header_rows=[0],
        body_rows=[1],
        row_views=[_build_row(1, "Age, years", ["52.3 (14.1)", "51.2 (13.0)", "<0.001", "0.12"])],
        n_rows=2,
        n_cols=5,
        metadata={
            "cleaned_rows": [
                ["Variable", "Overall", "Cases", "Controls", "P-value"],
            ]
        },
    )

    roles = {item.header_label: item.role for item in detect_column_roles(table)}

    assert roles["Overall"] == "overall"
    assert roles["Cases"] == "group"
    assert roles["Controls"] == "comparison_group"
    assert roles["P-value"] == "p_value"

    smd_table = table.model_copy(
        update={"n_cols": 2, "metadata": {"cleaned_rows": [["Variable", "SMD"]]}}
    )
    smd_roles = detect_column_roles(smd_table)
    assert smd_roles[1].role == "smd"


def test_value_pattern_detector_handles_required_examples_and_negatives() -> None:
    """Value-pattern detection should classify the required examples conservatively."""
    assert detect_value_pattern("412 (48.2)").pattern == "count_pct"
    assert detect_value_pattern("52.3 (14.1)").pattern == "mean_sd"
    assert detect_value_pattern("43.2 (35.0, 57.1)").pattern == "median_iqr"
    assert detect_value_pattern("<0.001").pattern == "p_value"
    assert detect_value_pattern("412").pattern == "n_only"

    assert detect_value_pattern("Cases").pattern == "unknown"
    assert detect_value_pattern("not reported").pattern == "unknown"
