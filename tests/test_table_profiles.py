"""Focused tests for deterministic table-family routing."""

from __future__ import annotations

from table1_parser.heuristics.table_profile import build_table_profile, table_profiles_to_payload
from table1_parser.schemas import NormalizedTable, RowView, TableProfile


def _build_row(row_idx: int, first_cell_raw: str, trailing: list[str]) -> RowView:
    """Create a compact RowView for routing tests."""
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
        indent_level=None,
        likely_role=None,
    )


def test_table_profile_marks_descriptive_characteristics_tables() -> None:
    """Baseline characteristic tables should route to the descriptive family."""
    table = NormalizedTable(
        table_id="tbl-desc",
        title="Table 1. Baseline characteristics",
        caption="Clinical characteristics by treatment group",
        header_rows=[0],
        body_rows=[1, 2, 3, 4],
        row_views=[
            _build_row(1, "Age, years", ["52.3 (14.1)", "51.2 (13.0)", "0.03"]),
            _build_row(2, "Sex", ["", "", ""]),
            _build_row(3, "Male", ["40 (40)", "10 (10)", "0.02"]),
            _build_row(4, "Female", ["60 (60)", "30 (30)", ""]),
        ],
        n_rows=5,
        n_cols=4,
        metadata={
            "cleaned_rows": [
                ["Characteristic", "Overall", "Cases", "P-value"],
                ["Age, years", "52.3 (14.1)", "51.2 (13.0)", "0.03"],
                ["Sex", "", "", ""],
                ["Male", "40 (40)", "10 (10)", "0.02"],
                ["Female", "60 (60)", "30 (30)", ""],
            ]
        },
    )

    profile = build_table_profile(table)

    assert profile.table_family == "descriptive_characteristics"
    assert "title_or_caption_mentions_characteristics" in profile.evidence


def test_table_profile_marks_estimate_result_tables() -> None:
    """Adjusted hazard-ratio tables should route to estimate_results."""
    table = NormalizedTable(
        table_id="tbl-est",
        title="Table 3. Adjusted hazard ratios for CKD progression",
        caption="Multivariable regression results",
        header_rows=[0],
        body_rows=[1, 2],
        row_views=[
            _build_row(1, "Proteinuria", ["1.42 (1.10, 1.83)", "<0.001"]),
            _build_row(2, "eGFR", ["0.78 (0.65, 0.94)", "0.01"]),
        ],
        n_rows=3,
        n_cols=3,
        metadata={
            "cleaned_rows": [
                ["Variable", "Adjusted HR (95% CI)", "P-value"],
                ["Proteinuria", "1.42 (1.10, 1.83)", "<0.001"],
                ["eGFR", "0.78 (0.65, 0.94)", "0.01"],
            ]
        },
    )

    profile = build_table_profile(table)

    assert profile.table_family == "estimate_results"
    assert "title_caption_or_header_mentions_estimate_metric" in profile.evidence


def test_table_profile_falls_back_to_unknown_when_evidence_is_weak() -> None:
    """Weakly structured tables should route to unknown until a supported family is clearer."""
    table = NormalizedTable(
        table_id="tbl-unknown",
        title="Table X",
        caption="Supplement",
        header_rows=[0],
        body_rows=[1, 2],
        row_views=[
            _build_row(1, "Random note", ["see text"]),
            _build_row(2, "Footnote", ["not reported"]),
        ],
        n_rows=3,
        n_cols=2,
        metadata={"cleaned_rows": [["Section", "Value"], ["Random note", "see text"], ["Footnote", "not reported"]]},
    )

    profile = build_table_profile(table)

    assert profile.table_family == "unknown"


def test_table_profile_schema_and_payload_round_trip() -> None:
    """TableProfile should serialize cleanly through the JSON payload helper."""
    profile = TableProfile(
        table_id="tbl-profile",
        table_family="descriptive_characteristics",
        family_confidence=0.91,
        evidence=["row_structure_contains_parent_level_blocks"],
    )

    payload = table_profiles_to_payload([profile])

    assert payload[0]["table_id"] == "tbl-profile"
    assert payload[0]["table_family"] == "descriptive_characteristics"
