# Design Index

This file is a guide for coding agents and developers who need the main design-intent documents for this repository.

Read `AGENTS.md` first.

Then use the documents below as needed.

## Core Architecture

- `docs/design/codex_build_spec.md`
  Core project architecture and original schema/build spec.

- `docs/design/parsing_process.md`
  Short user-facing overview of the intended pipeline:
  `PDF -> ExtractedTable -> NormalizedTable -> TableDefinition -> ParsedTable`

- `docs/design/parsing_output_design.md`
  Current JSON artifact design, canonical models, and output-file intent.

- `docs/design/value_parsing_spec.md`
  Planned symbol canonicalization and Table 1 `n (%)` parsing heuristics for the later value-parsing path.

- `docs/design/multitable_architecture_spec.md`
  Planned routing stage, descriptive-vs-estimate table families, and estimate-table schemas for mixed-table papers.

- `docs/implementation/multitable_implementation_plan.md`
  Stepwise implementation plan for `TableProfile`, LLM gating, and later estimate-table parsing.

## Value-Free Semantic Stage

- `docs/design/table_definition_scope.md`
  Scope for the proposed intermediate `TableDefinition` stage between `NormalizedTable` and `ParsedTable`.

- `docs/design/table_definition_schema.md`
  Proposed Pydantic schema design for `TableDefinition` and related models.

- `docs/implementation/table_definition_implementation_plan.md`
  Implementation plan for the SQL-query-oriented `TableDefinition` phase, including row-variable, categorical-level, and column-definition goals.

- `docs/implementation/column_grouping_semantics_plan.md`
  Focused implementation plan for the newer grouped-column semantics work inside deterministic `TableDefinition` assembly.

- `docs/implementation/normalized_column_repair_plan.md`
  Focused implementation plan for conservative normalization-time repair of split value columns and missed header rows.

## Supporting References

- `docs/design/paper_markdown_spec.md`
  Design intent for `paper_markdown.md`, including expected variation in section naming and heading structure.

- `docs/design/llm_integration.md`
  Current LLM integration and trace-artifact behavior.

- `docs/design/llm_semantic_inference_phase.md`
  Design for the next LLM phase: markdown-based paper retrieval, semantic interpretation, and adjudication.

- `docs/implementation/llm_semantic_cli_changes.md`
  Narrow CLI wiring plan for running semantic LLM table-definition inference during `parse`.

- `docs/implementation/llm_semantic_inference_steps.md`
  Brief implementation checklist for the LLM semantic inference phase.

- `docs/r_visualization.md`
  How current JSON outputs are inspected in R.

## When To Read These

- If you are changing extraction, normalization, heuristics, LLM parsing, validation, or final exports:
  read `docs/design/codex_build_spec.md` and `docs/design/parsing_output_design.md`.

- If you are changing symbol normalization, parser-facing text canonicalization, or categorical `n (%)` value parsing:
  read `docs/design/value_parsing_spec.md`.

- If you are changing mixed-table routing, LLM gating by table family, or estimate-result table parsing:
  read `docs/design/multitable_architecture_spec.md`.
  For concrete sequencing, also read `docs/implementation/multitable_implementation_plan.md`.

- If you are working on the new value-free semantic stage for database matching:
  read `docs/design/table_definition_scope.md`, `docs/design/table_definition_schema.md`, and `docs/implementation/table_definition_implementation_plan.md`.

- If you are updating user-facing explanations of the pipeline:
  read `docs/design/parsing_process.md`.

- If you are changing markdown extraction, section parsing, or table-context retrieval:
  read `docs/design/paper_markdown_spec.md` and `docs/design/llm_semantic_inference_phase.md`.
