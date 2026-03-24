"""Validation for deterministic TableProfile artifacts."""

from __future__ import annotations

from table1_parser.schemas import TableProfile


def validate_table_profile(profile: TableProfile) -> TableProfile:
    """Validate one deterministic table-family routing decision."""
    if profile.table_family == "descriptive_characteristics":
        _require(profile.should_run_llm_semantics, "Descriptive tables must currently allow semantic LLM interpretation.")
    else:
        _require(
            not profile.should_run_llm_semantics,
            "Only descriptive_characteristics tables may currently enable semantic LLM interpretation.",
        )
    return profile


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
