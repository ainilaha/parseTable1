"""LLM semantic interpreter for TableDefinition artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from table1_parser.llm.client import LLMClient
from table1_parser.llm.semantic_prompts import build_llm_semantic_input_payload, build_llm_semantic_prompt
from table1_parser.llm.semantic_schemas import LLMSemanticInputPayload, LLMSemanticTableDefinition
from table1_parser.schemas import NormalizedTable, TableContext, TableDefinition
from table1_parser.validation import validate_llm_semantic_table_definition


class LLMSemanticInterpretationError(Exception):
    """Structured failure for invalid or unsafe LLM semantic interpretations."""

    def __init__(
        self,
        message: str,
        *,
        payload: LLMSemanticInputPayload | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.payload = payload
        self.raw_response = raw_response


class LLMSemanticTableDefinitionParser:
    """Call an LLM for semantic TableDefinition interpretation and validate the result."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def parse(
        self,
        table: NormalizedTable,
        deterministic_table_definition: TableDefinition,
        retrieved_context: TableContext,
        *,
        trace_dir: str | Path | None = None,
    ) -> LLMSemanticTableDefinition:
        """Produce a validated LLM semantic interpretation for one normalized table."""
        payload = build_llm_semantic_input_payload(table, deterministic_table_definition, retrieved_context)
        schema = LLMSemanticTableDefinition.model_json_schema()
        prompt = build_llm_semantic_prompt(payload, schema)
        raw_response = self.client.structured_completion(
            prompt,
            schema,
            response_model=LLMSemanticTableDefinition,
        )
        try:
            result = LLMSemanticTableDefinition.model_validate(raw_response)
            validated = validate_llm_semantic_table_definition(result, table, retrieved_context)
        except (ValidationError, ValueError) as exc:
            raise LLMSemanticInterpretationError(
                "Invalid structured LLM semantic interpretation.",
                payload=payload,
                raw_response=raw_response,
            ) from exc
        if trace_dir is not None:
            _write_trace_artifacts(
                trace_dir=trace_dir,
                deterministic_table_definition=deterministic_table_definition,
                retrieved_context=retrieved_context,
                payload=payload,
                raw_response=raw_response,
                result=validated,
            )
        return validated


def _utc_timestamp() -> str:
    """Return a compact UTC ISO 8601 timestamp with trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a small JSON artifact with stable formatting."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_trace_artifacts(
    *,
    trace_dir: str | Path,
    deterministic_table_definition: TableDefinition,
    retrieved_context: TableContext,
    payload: LLMSemanticInputPayload,
    raw_response: dict[str, Any],
    result: LLMSemanticTableDefinition,
) -> None:
    """Write compact trace artifacts for one semantic LLM interpretation."""
    timestamp = _utc_timestamp()
    trace_path = Path(trace_dir)
    trace_path.mkdir(parents=True, exist_ok=True)
    _write_json(
        trace_path / "table_definition_deterministic.json",
        {
            "report_timestamp": timestamp,
            "table_id": deterministic_table_definition.table_id,
            "table_definition": deterministic_table_definition.model_dump(mode="json"),
        },
    )
    _write_json(
        trace_path / "table_definition_context.json",
        {
            "report_timestamp": timestamp,
            "table_id": deterministic_table_definition.table_id,
            "context": retrieved_context.model_dump(mode="json"),
        },
    )
    _write_json(
        trace_path / "table_definition_llm_input.json",
        {
            "report_timestamp": timestamp,
            "table_id": deterministic_table_definition.table_id,
            "payload": payload.model_dump(mode="json"),
        },
    )
    _write_json(
        trace_path / "table_definition_llm_output.json",
        {
            "report_timestamp": timestamp,
            "table_id": deterministic_table_definition.table_id,
            "response": raw_response,
        },
    )
    _write_json(
        trace_path / "table_definition_llm_interpretation.json",
        {
            "report_timestamp": timestamp,
            "table_id": deterministic_table_definition.table_id,
            "interpretation": result.model_dump(mode="json"),
        },
    )
    (trace_path / "table_definition_llm_diff.txt").write_text(
        f"timestamp: {timestamp}\n" + _diff(deterministic_table_definition, result) + "\n",
        encoding="utf-8",
    )


def _diff(deterministic: TableDefinition, llm_result: LLMSemanticTableDefinition) -> str:
    """Create a small human-readable diff between deterministic and LLM outputs."""
    lines: list[str] = []
    deterministic_variables = {variable.row_start: variable for variable in deterministic.variables}
    for variable in llm_result.variables:
        baseline = deterministic_variables.get(variable.row_start)
        if baseline is None:
            lines.append(f"variable added at rows {variable.row_start}-{variable.row_end}: {variable.variable_label}")
            continue
        if baseline.variable_type != variable.variable_type:
            lines.append(
                f"variable type changed at {variable.row_start}: {baseline.variable_type} -> {variable.variable_type}"
            )
    deterministic_columns = {column.col_idx: column for column in deterministic.column_definition.columns}
    for column in llm_result.column_definition.columns:
        baseline = deterministic_columns.get(column.col_idx)
        if baseline is None:
            lines.append(f"column added at {column.col_idx}: role={column.inferred_role}")
            continue
        if baseline.inferred_role != column.inferred_role:
            lines.append(
                f"column role changed at {column.col_idx}: {baseline.inferred_role} -> {column.inferred_role}"
            )
    if llm_result.notes:
        lines.append(f"notes added: {len(llm_result.notes)}")
    return "\n".join(lines) if lines else "no deterministic-to-llm semantic changes detected"
