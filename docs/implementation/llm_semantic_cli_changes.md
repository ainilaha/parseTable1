# LLM Semantic CLI Changes

This document describes the next narrow change: wiring semantic LLM table-definition inference into `table1-parser parse`.

## Goal

Make `parse` run semantic LLM table-definition inference when LLM configuration is available, while keeping deterministic outputs as the baseline.

## Intended CLI Behavior

`table1-parser parse <paper.pdf>` should:

1. always write:
   - `extracted_tables.json`
   - `normalized_tables.json`
   - `table_definitions.json`
   - `paper_markdown.md`
   - `paper_sections.json`
   - `paper_variable_inventory.json`
   - `table_contexts/*.json`
2. also write `table_definitions_llm.json` when semantic LLM configuration is available

Add:

- `--no-llm-semantic`

This flag disables semantic LLM inference even when configuration is present.

## Configuration Behavior

Semantic LLM inference should be:

- on by default when the required environment variables are present
- skipped when they are not present
- skipped when `--no-llm-semantic` is set

If semantic LLM inference is not turned off, but configuration is missing, `parse` should warn clearly and continue with deterministic outputs only.

Example warning:

```text
LLM semantic interpretation skipped: OPENAI_API_KEY is required when LLM_PROVIDER=openai. Use --no-llm-semantic to suppress this warning.
```

## Output

When semantic LLM inference runs, write:

```text
outputs/papers/<paper_stem>/table_definitions_llm.json
```

This file should be a list of validated `LLMSemanticTableDefinition` objects, one per table.

## Scope

This change should only add orchestration and output wiring.

Do not add:

- adjudication
- `ParsedTable`
- value parsing
- database matching

## Modules To Touch

- `table1_parser/cli.py`
  add `--no-llm-semantic`, config detection, warning behavior, and output writing
- `table1_parser/llm/client.py`
  reuse provider/config checks rather than duplicating them
- `table1_parser/config.py`
  keep environment-driven model/provider settings as the source of truth

## Validation Rule

Only write `table_definitions_llm.json` after the semantic LLM output has passed the existing row/column safety validation.

## Tests

Add CLI tests for:

- semantic LLM enabled and output written
- semantic LLM missing and warning emitted
- `--no-llm-semantic` skipping the LLM path
- deterministic outputs still written in all cases
