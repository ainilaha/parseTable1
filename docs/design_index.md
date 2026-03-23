# Design Index

This file is a guide for coding agents and developers who need the main design-intent documents for this repository.

Read `AGENTS.md` first.

Then use the documents below as needed.

## Core Architecture

- `docs/codex_build_spec.md`
  Core project architecture and original schema/build spec.

- `docs/parsing_process.md`
  Short user-facing overview of the intended pipeline:
  `PDF -> ExtractedTable -> NormalizedTable -> TableDefinition -> ParsedTable`

- `docs/parsing_output_design.md`
  Current JSON artifact design, canonical models, and output-file intent.

- `docs/value_parsing_spec.md`
  Planned symbol canonicalization and Table 1 `n (%)` parsing heuristics for the later value-parsing path.

## Value-Free Semantic Stage

- `docs/table_definition_scope.md`
  Scope for the proposed intermediate `TableDefinition` stage between `NormalizedTable` and `ParsedTable`.

- `docs/table_definition_schema.md`
  Proposed Pydantic schema design for `TableDefinition` and related models.

- `docs/table_definition_implementation_plan.md`
  Implementation plan for the SQL-query-oriented `TableDefinition` phase, including row-variable, categorical-level, and column-definition goals.

## Supporting References

- `docs/paper_markdown_spec.md`
  Design intent for `paper_markdown.md`, including expected variation in section naming and heading structure.

- `docs/llm_integration.md`
  Current LLM integration and trace-artifact behavior.

- `docs/llm_semantic_inference_phase.md`
  Design for the next LLM phase: markdown-based paper retrieval, semantic interpretation, and adjudication.

- `docs/llm_semantic_cli_changes.md`
  Narrow CLI wiring plan for running semantic LLM table-definition inference during `parse`.

- `docs/llm_semantic_inference_steps.md`
  Brief implementation checklist for the LLM semantic inference phase.

- `docs/r_visualization.md`
  How current JSON outputs are inspected in R.

## When To Read These

- If you are changing extraction, normalization, heuristics, LLM parsing, validation, or final exports:
  read `docs/codex_build_spec.md` and `docs/parsing_output_design.md`.

- If you are changing symbol normalization, parser-facing text canonicalization, or categorical `n (%)` value parsing:
  read `docs/value_parsing_spec.md`.

- If you are working on the new value-free semantic stage for database matching:
  read `docs/table_definition_scope.md`, `docs/table_definition_schema.md`, and `docs/table_definition_implementation_plan.md`.

- If you are updating user-facing explanations of the pipeline:
  read `docs/parsing_process.md`.

- If you are changing markdown extraction, section parsing, or table-context retrieval:
  read `docs/paper_markdown_spec.md` and `docs/llm_semantic_inference_phase.md`.
