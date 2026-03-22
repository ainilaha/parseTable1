# TableDefinition Implementation Plan

This document guides the next phase: building a value-free semantic stage that defines the rows and columns of a Table 1 in a form suitable for downstream SQL-query generation.

## Goal

Implement `TableDefinition` as the stage between `NormalizedTable` and `ParsedTable`.

This phase should answer:

- which variables define the table rows
- which of those variables are categorical
- what the categorical levels are
- what the columns represent
- what grouping or stratifying variable likely defines the columns

This phase should not extract or parse the printed values.

The expected downstream use is:

- `TableDefinition` identifies the paper-facing row and column semantics
- an R-based intermediary can use that structure to query the database
- existing R visualization tooling can then help inspect matched variables, categories, and retrieved results

## Pipeline Position

Target pipeline:

```text
PDF -> ExtractedTable -> NormalizedTable -> TableDefinition -> ParsedTable
```

For now, `parse` should continue to run once and write all available artifacts. After this phase, that should include `table_definitions.json`.

## Main Output

Add a new canonical schema:

- `table1_parser/schemas/table_definition.py`

and a new persisted file:

- `parseTable1.out/papers/<paper_stem>/table_definitions.json`

The file should be a JSON array of direct `TableDefinition.model_dump(mode="json")` payloads.

## Required Semantics

Each `TableDefinition` should preserve:

- `table_id`
- `title`
- `caption`
- row variable definitions
- categorical levels where present
- column definitions
- grouping hints
- confidence fields
- notes

Each row variable should preserve both:

- the printed label from the paper
- a normalized label suitable for matching to database fields

Each categorical level should preserve both:

- the printed level label
- a normalized label suitable for matching to coded category values

Each column should preserve both:

- the printed column label
- a normalized label suitable for matching to a database grouping variable

## Scope for This Phase

Implement:

1. Pydantic schema for `TableDefinition`
2. Deterministic row-structure inference from `NormalizedTable`
3. Deterministic column inference from normalized headers
4. Optional LLM refinement interface for ambiguous cases
5. Validation of the `TableDefinition`
6. CLI export from `table1-parser parse`
7. Tests and docs

Do not implement:

- value extraction
- `ParsedTable`
- database matching itself
- SQL generation itself

This phase should prepare for those later steps by emitting a structure that is easy for an R workflow to consume.

## Recommended Modules

- `table1_parser/schemas/table_definition.py`
- `table1_parser/heuristics/table_definition_rows.py`
- `table1_parser/heuristics/table_definition_columns.py`
- `table1_parser/heuristics/table_definition_builder.py`
- `table1_parser/validation/table_definition.py`

If LLM refinement is added in this phase, keep it separate from deterministic heuristics.

## Deterministic Row Inference

Use `NormalizedTable` signals first:

- `header_rows`
- `body_rows`
- `row_views`
- cleaned rows
- indentation information

Infer at least:

- variable rows
- level rows
- section/header-like rows inside the body
- count rows such as `n`

Expected row outcomes:

- continuous variable with no levels
- categorical variable with one or more levels
- binary variable represented as levels or a single summary row
- unknown/ambiguous variable

## Deterministic Column Inference

Use normalized header rows and column text to infer:

- `overall`
- subgroup column
- comparison group column
- `p_value`
- `smd`
- `unknown`

Also try to infer the grouping concept, such as:

- disease status
- exposure category
- case/control status
- quartile group

The result should support downstream matching to the database field that created the table columns.

That downstream matching layer may live in R, so the output should stay simple, explicit, and JSON-first.

## LLM Role

LLM use should be optional and only for semantic ambiguity.

Use the LLM to refine:

- whether a row is a parent variable or a section label
- whether nearby rows are categorical levels under a parent variable
- what the column grouping concept most likely is
- messy multi-row header interpretation

Do not use the LLM to:

- invent rows
- invent columns
- infer values
- replace deterministic extraction or normalization

## Validation Requirements

Validation should ensure:

- all referenced `row_idx` values exist
- all referenced `col_idx` values exist
- level rows belong to a valid parent variable
- variable row spans are coherent
- column roles are internally consistent
- LLM refinement does not introduce rows or columns absent from the normalized table

## CLI Requirements

Update `table1-parser parse` so it writes:

- `extracted_tables.json`
- `normalized_tables.json`
- `table_definitions.json`

from one pipeline run.

`extract` and `normalize` should remain available as stage-specific commands.

## Test Requirements

Add tests for:

- `TableDefinition` schema validation
- deterministic row-variable grouping
- categorical level extraction
- column-role inference
- grouping-variable hints
- validation failures for bad row/column references
- `parse` writing `table_definitions.json`

Use the sample papers in `testpapers/` where helpful.

## Success Criteria

This phase is successful when a user can run:

```bash
table1-parser parse path/to/paper.pdf
```

and obtain a `table_definitions.json` file that is suitable for a downstream tool to:

- identify candidate database fields for row variables
- identify candidate coded values for categorical levels
- identify the database field likely used to construct the table columns
- hand the result to an R-based database-query and visualization workflow

without relying on table cell values.
