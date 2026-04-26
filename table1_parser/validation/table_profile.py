"""Validation for deterministic TableProfile artifacts."""

from __future__ import annotations

from table1_parser.schemas import TableProfile


def validate_table_profile(profile: TableProfile) -> TableProfile:
    """Validate one deterministic table-family routing decision."""
    _require(bool(profile.table_id), "Table profiles must carry table_id.")
    return profile


def _require(condition: bool, message: str) -> None:
    """Raise a value error when a validation condition fails."""
    if not condition:
        raise ValueError(message)
