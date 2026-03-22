"""I/O helpers for persisted normalized-table artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from table1_parser.schemas import NormalizedTable


def normalized_tables_to_payload(tables: list[NormalizedTable]) -> list[dict[str, object]]:
    """Serialize normalized tables as a JSON-friendly payload."""
    return [table.model_dump(mode="json") for table in tables]


def write_normalized_tables(path: str | Path, tables: list[NormalizedTable]) -> Path:
    """Write normalized tables to a JSON file with stable formatting."""
    output_path = Path(path)
    payload = normalized_tables_to_payload(tables)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def load_normalized_tables(path: str | Path) -> list[NormalizedTable]:
    """Load normalized tables from a JSON artifact and validate them."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Normalized table JSON must be an object or array of objects.")
    return [NormalizedTable.model_validate(item) for item in payload]
