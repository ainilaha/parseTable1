"""LLM-assisted parser for refining heuristic table interpretation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from table1_parser.config import Settings
from table1_parser.heuristics import classify_rows, detect_column_roles, group_variable_blocks
from table1_parser.heuristics.models import ColumnRoleGuess, RowClassification, VariableBlock
from table1_parser.llm.client import LLMClient, build_llm_client
from table1_parser.llm.prompts import build_llm_input_payload, build_llm_prompt
from table1_parser.llm.schemas import LLMInputPayload, LLMTableInterpretation
from table1_parser.schemas import NormalizedTable


class LLMInterpretationError(Exception):
    """Structured failure for invalid or malformed LLM interpretations."""

    def __init__(
        self,
        message: str,
        *,
        payload: LLMInputPayload | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.payload = payload
        self.raw_response = raw_response


class LLMTableParser:
    """Build a prompt, call an LLM client, and validate the structured interpretation."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def parse(
        self,
        table: NormalizedTable,
        *,
        trace_dir: str | Path | None = None,
    ) -> LLMTableInterpretation:
        """Produce a typed LLM interpretation from normalized and heuristic table state."""
        row_classifications = classify_rows(table)
        variable_blocks = group_variable_blocks(table, row_classifications)
        column_roles = detect_column_roles(table)
        payload = build_llm_input_payload(
            table=table,
            row_classifications=row_classifications,
            variable_blocks=variable_blocks,
            column_roles=column_roles,
        )
        schema = LLMTableInterpretation.model_json_schema()
        prompt = build_llm_prompt(payload, schema)
        raw_response = self.client.structured_completion(
            prompt,
            schema,
            response_model=LLMTableInterpretation,
        )
        try:
            result = LLMTableInterpretation.model_validate(raw_response)
        except ValidationError as exc:
            raise LLMInterpretationError(
                "Invalid structured LLM interpretation.",
                payload=payload,
                raw_response=raw_response,
            ) from exc
        if trace_dir is not None:
            _write_trace_artifacts(
                trace_dir=trace_dir,
                table=table,
                row_classifications=row_classifications,
                variable_blocks=variable_blocks,
                column_roles=column_roles,
                payload=payload,
                raw_response=raw_response,
                result=result,
            )
        return result


def parse_table_with_llm(table: NormalizedTable, client: LLMClient) -> LLMTableInterpretation:
    """Convenience wrapper for one-off LLM-assisted parsing."""
    return LLMTableParser(client).parse(table)


def parse_table_with_configured_llm(
    table: NormalizedTable,
    *,
    settings: Settings | None = None,
    trace_dir: str | Path | None = None,
) -> LLMTableInterpretation:
    """Convenience wrapper that builds a provider client from environment-backed settings."""
    client = build_llm_client(settings=settings)
    return LLMTableParser(client).parse(table, trace_dir=trace_dir)


def _utc_timestamp() -> str:
    """Return a compact UTC ISO 8601 timestamp with trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a small JSON artifact with stable formatting."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_trace_artifacts(
    *,
    trace_dir: str | Path,
    table: NormalizedTable,
    row_classifications: list[RowClassification],
    variable_blocks: list[VariableBlock],
    column_roles: list[ColumnRoleGuess],
    payload: LLMInputPayload,
    raw_response: dict[str, Any],
    result: LLMTableInterpretation,
) -> None:
    """Write small debug trace artifacts for one LLM parse."""
    timestamp = _utc_timestamp()
    trace_path = Path(trace_dir)
    trace_path.mkdir(parents=True, exist_ok=True)

    heuristics = {
        "table_id": table.table_id,
        "row_classifications": [item.model_dump(mode="json") for item in row_classifications],
        "variables": [
            {
                "variable_row_idx": block.variable_row_idx,
                "row_start": block.row_start,
                "row_end": block.row_end,
                "variable_label": block.variable_label,
                "variable_type": block.variable_kind,
                "levels": block.level_row_indices,
            }
            for block in variable_blocks
        ],
        "columns": [
            {
                "col_idx": role.col_idx,
                "header_label": role.header_label,
                "inferred_role": role.role,
                "confidence": role.confidence,
            }
            for role in column_roles
        ],
        "notes": [],
    }
    _write_json(
        trace_path / "heuristics.json",
        {"report_timestamp": timestamp, "table_id": table.table_id, **heuristics},
    )
    _write_json(
        trace_path / "llm_input.json",
        {
            "report_timestamp": timestamp,
            "table_id": table.table_id,
            "payload": payload.model_dump(mode="json"),
        },
    )
    _write_json(
        trace_path / "llm_output.json",
        {"report_timestamp": timestamp, "table_id": table.table_id, "response": raw_response},
    )
    _write_json(
        trace_path / "final_interpretation.json",
        {
            "report_timestamp": timestamp,
            "table_id": table.table_id,
            "interpretation": result.model_dump(mode="json"),
        },
    )
    lines: list[str] = []
    heuristic_vars = {item["row_start"]: item for item in heuristics.get("variables", [])}
    final_vars = {item.row_start: item for item in result.variables}
    for row_start, final_var in sorted(final_vars.items()):
        heuristic_var = heuristic_vars.get(row_start)
        if heuristic_var is None:
            lines.append(f"variable added at rows {final_var.row_start}-{final_var.row_end}: {final_var.variable_name}")
            continue
        if heuristic_var["row_end"] != final_var.row_end:
            lines.append(f"variable rows changed at {row_start}: {heuristic_var['row_end']} -> {final_var.row_end}")
        if heuristic_var["variable_type"] != final_var.variable_type:
            lines.append(f"variable type changed at {row_start}: {heuristic_var['variable_type']} -> {final_var.variable_type}")
        heuristic_levels = heuristic_var.get("levels", [])
        final_levels = [level.row_idx for level in final_var.levels]
        if heuristic_levels != final_levels:
            lines.append(f"variable levels changed at {row_start}: {heuristic_levels} -> {final_levels}")
    for row_start, heuristic_var in sorted(heuristic_vars.items()):
        if row_start not in final_vars:
            lines.append(
                f"variable removed at rows {heuristic_var['row_start']}-{heuristic_var['row_end']}: {heuristic_var['variable_label']}"
            )
    heuristic_columns = {item["col_idx"]: item for item in heuristics.get("columns", [])}
    final_columns = {item.col_idx: item for item in result.columns}
    for col_idx, final_col in sorted(final_columns.items()):
        heuristic_col = heuristic_columns.get(col_idx)
        if heuristic_col is None:
            lines.append(f"column added at {col_idx}: role={final_col.inferred_role}")
            continue
        if heuristic_col["inferred_role"] != final_col.inferred_role:
            lines.append(f"column role changed at {col_idx}: {heuristic_col['inferred_role']} -> {final_col.inferred_role}")
    if result.notes:
        lines.append(f"notes added: {len(result.notes)}")
    (trace_path / "diff.txt").write_text(
        f"timestamp: {timestamp}\n" + ("\n".join(lines) if lines else "no heuristic-to-llm changes detected") + "\n",
        encoding="utf-8",
    )
