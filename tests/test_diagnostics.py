"""Focused tests for parse-quality diagnostics."""

from __future__ import annotations

from datetime import datetime

from table1_parser.diagnostics import build_parse_quality_report
from table1_parser.heuristics.models import ColumnRoleGuess, RowClassification, VariableBlock
from table1_parser.schemas import NormalizedTable, RowView


def _build_row(row_idx: int, first_cell_raw: str, trailing: list[str]) -> RowView:
    raw_cells = [first_cell_raw, *trailing]
    return RowView(
        row_idx=row_idx,
        raw_cells=raw_cells,
        first_cell_raw=first_cell_raw,
        first_cell_normalized=first_cell_raw,
        first_cell_alpha_only=first_cell_raw,
        nonempty_cell_count=sum(bool(cell) for cell in raw_cells),
        numeric_cell_count=sum(any(char.isdigit() for char in cell) for cell in raw_cells),
        has_trailing_values=any(bool(cell) for cell in trailing),
        indent_level=None,
        likely_role=None,
    )


def _build_table(row_views: list[RowView], cleaned_rows: list[list[str]] | None = None) -> NormalizedTable:
    return NormalizedTable(
        table_id="tbl-diagnostics",
        header_rows=[0],
        body_rows=[row_view.row_idx for row_view in row_views],
        row_views=row_views,
        n_rows=len(row_views) + 1,
        n_cols=max((len(row.raw_cells) for row in row_views), default=0),
        metadata={"cleaned_rows": cleaned_rows or [["Variable", "Overall", "P-value"]]},
    )


def test_warning_when_many_rows_are_unknown() -> None:
    """Unknown-row rates above the warning threshold should be surfaced."""
    rows = [_build_row(1, "Age", ["52.1"]), _build_row(2, "?", ["text"]), _build_row(3, "?", ["text"]), _build_row(4, "Male", ["34"])]
    table = _build_table(rows)
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=1, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=2, classification="unknown", confidence=0.4),
            RowClassification(row_idx=3, classification="unknown", confidence=0.4),
            RowClassification(row_idx=4, classification="level_row", confidence=0.8),
        ],
        [VariableBlock(variable_row_idx=1, row_start=1, row_end=1, variable_label="Age", variable_kind="continuous")],
    )

    assert report.summary.unknown_row_fraction > 0.25
    assert any(item.code == "unknown_row_fraction_warning" for item in report.table_diagnostics)


def test_suspicious_when_most_rows_are_unknown() -> None:
    """Unknown-row rates above 0.50 should be marked suspicious."""
    rows = [
        _build_row(1, "", ["x"]),
        _build_row(2, "", ["y"]),
        _build_row(3, "Age", ["52.1"]),
        _build_row(4, "", ["z"]),
        _build_row(5, "Male", ["34"]),
    ]
    table = _build_table(rows)
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=1, classification="unknown", confidence=0.4),
            RowClassification(row_idx=2, classification="unknown", confidence=0.4),
            RowClassification(row_idx=3, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=4, classification="unknown", confidence=0.4),
            RowClassification(row_idx=5, classification="level_row", confidence=0.8),
        ],
        [VariableBlock(variable_row_idx=3, row_start=3, row_end=3, variable_label="Age", variable_kind="continuous")],
    )

    assert report.summary.unknown_row_fraction > 0.50
    assert any(item.code == "unknown_row_fraction_suspicious" for item in report.table_diagnostics)


def test_likely_failure_when_nearly_all_rows_are_unknown() -> None:
    """Unknown-row rates above 0.70 should be treated as likely failure."""
    rows = [_build_row(1, "", ["x"]), _build_row(2, "", ["y"]), _build_row(3, "", ["z"]), _build_row(4, "?", ["w"])]
    table = _build_table(rows)
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=1, classification="unknown", confidence=0.4),
            RowClassification(row_idx=2, classification="unknown", confidence=0.4),
            RowClassification(row_idx=3, classification="unknown", confidence=0.4),
            RowClassification(row_idx=4, classification="unknown", confidence=0.4),
        ],
        [],
    )

    assert report.summary.unknown_row_fraction > 0.70
    assert any(item.code == "unknown_row_fraction_likely_failure" for item in report.table_diagnostics)


def test_suspicious_numeric_column_full_of_text_is_flagged() -> None:
    """A column inferred as numeric/statistical should be flagged when it is mostly text."""
    rows = [_build_row(1, "Age", ["cases", "alpha"]), _build_row(2, "BMI", ["controls", "beta"]), _build_row(3, "Sex", ["group", "gamma"])]
    table = _build_table(rows)
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=1, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=2, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=3, classification="variable_header", confidence=0.8),
        ],
        [VariableBlock(variable_row_idx=1, row_start=1, row_end=1, variable_label="Age", variable_kind="continuous")],
        [ColumnRoleGuess(col_idx=1, header_label="Overall", role="overall", confidence=0.95)],
    )

    assert any(item.code == "non_numeric_statistical_column" for item in report.column_diagnostics)


def test_invalid_p_value_column_is_flagged() -> None:
    """A p-value column with non-p-value content should be reported."""
    rows = [_build_row(1, "Age", ["alpha"]), _build_row(2, "BMI", ["beta"]), _build_row(3, "Sex", ["gamma"])]
    table = _build_table(rows)
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=1, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=2, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=3, classification="variable_header", confidence=0.8),
        ],
        [VariableBlock(variable_row_idx=1, row_start=1, row_end=1, variable_label="Age", variable_kind="continuous")],
        [ColumnRoleGuess(col_idx=1, header_label="P-value", role="p_value", confidence=0.98)],
    )

    assert any(item.code == "invalid_p_value_column" for item in report.column_diagnostics)


def test_report_includes_valid_utc_timestamp() -> None:
    """Diagnostics reports should include a UTC ISO-style timestamp."""
    table = _build_table([_build_row(1, "Age", ["52.1"])])
    report = build_parse_quality_report(
        table,
        [RowClassification(row_idx=1, classification="continuous_variable_row", confidence=0.9)],
        [VariableBlock(variable_row_idx=1, row_start=1, row_end=1, variable_label="Age", variable_kind="continuous")],
    )

    assert report.report_timestamp.endswith("Z")
    parsed = datetime.fromisoformat(report.report_timestamp.replace("Z", "+00:00"))
    assert parsed.utcoffset() is not None


def test_healthy_small_example_is_not_over_flagged() -> None:
    """A small healthy synthetic table should not accumulate major warnings."""
    rows = [
        _build_row(1, "Age, years", ["52.3 (14.1)", "<0.001"]),
        _build_row(2, "Sex", ["", ""]),
        _build_row(3, "Male", ["412 (48.2)", ""]),
        _build_row(4, "Female", ["443 (51.8)", ""]),
    ]
    table = _build_table(rows)
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=1, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=2, classification="variable_header", confidence=0.85),
            RowClassification(row_idx=3, classification="level_row", confidence=0.8),
            RowClassification(row_idx=4, classification="level_row", confidence=0.8),
        ],
        [
            VariableBlock(variable_row_idx=1, row_start=1, row_end=1, variable_label="Age, years", variable_kind="continuous"),
            VariableBlock(variable_row_idx=2, row_start=2, row_end=4, variable_label="Sex", variable_kind="categorical", level_row_indices=[3, 4]),
        ],
        [
            ColumnRoleGuess(col_idx=1, header_label="Overall", role="overall", confidence=0.95),
            ColumnRoleGuess(col_idx=2, header_label="P-value", role="p_value", confidence=0.98),
        ],
    )

    assert not any(item.severity == "error" for item in report.table_diagnostics + report.row_diagnostics + report.column_diagnostics)
    assert report.summary.unknown_row_count == 0


def test_suspicious_three_row_header_is_flagged() -> None:
    """Three detected header rows should surface a conservative table-level warning."""
    rows = [_build_row(3, "Age, years", ["52.1"]), _build_row(4, "Male", ["34"])]
    table = NormalizedTable(
        table_id="tbl-header-warning",
        header_rows=[0, 1, 2],
        body_rows=[3, 4],
        row_views=rows,
        n_rows=5,
        n_cols=2,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall"],
                ["", "n"],
                ["", "%"],
            ],
            "header_detection": {
                "source": "horizontal_rules",
                "rule_strength": "moderate",
                "rule_based_headers": [0, 1, 2],
                "content_based_headers": [0],
                "rule_content_disagreement": True,
            },
        },
    )
    report = build_parse_quality_report(
        table,
        [
            RowClassification(row_idx=3, classification="continuous_variable_row", confidence=0.9),
            RowClassification(row_idx=4, classification="level_row", confidence=0.8),
        ],
        [VariableBlock(variable_row_idx=3, row_start=3, row_end=3, variable_label="Age", variable_kind="continuous")],
    )

    assert any(item.code == "suspicious_header_row_count" for item in report.table_diagnostics)
    assert any(item.code == "header_rule_content_disagreement" for item in report.table_diagnostics)
