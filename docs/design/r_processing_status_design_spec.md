# R Processing Status Design Spec

## Purpose

Expose table processing outcomes in R so a user can see:

- which tables succeeded
- which tables were rescued
- which tables failed
- what rescue attempts were considered, run, and successful
- at which stage a table failed

This design is for inspection and explanation.
It does not change parser behavior.

## Inputs

The R layer should treat these as first-class paper outputs:

- `extracted_tables.json`
- `normalized_tables.json`
- `table_definitions.json`
- `parsed_tables.json`
- `table_processing_status.json`
- `table_variable_plausibility_llm.json` when present

## Design Goals

- make failure visible immediately
- avoid silent empty-success interpretation
- connect processing status to the existing table inspection workflow
- stay base-R and additive
- preserve current helpers and extend them rather than replace them

## Core R Additions

### 1. Extend `load_paper_outputs()`

`load_paper_outputs()` should also load:

- `parsed_tables`
- `table_processing_status`

These should be available alongside the existing deterministic artifacts and the optional variable-plausibility review artifact.

### 2. Add paper-level summary view

Add:

- `summarize_table_processing(paper_dir)`

This should print one row per table.

Required columns:

- `table_index`
- `table_id`
- `title`
- `status`
- `failure_stage`
- `failure_reason`
- `attempt_count`
- `successful_attempt_count`
- `variable_count`
- `usable_column_count`
- `value_count`

Preferred extra columns when available:

- `table_family`
- `grid_refinement_source`

Purpose:
- give the user a fast answer to “what happened in this paper?”

### 3. Add table-level detail view

Add:

- `show_table_processing(paper_dir, table_index = 0L)`

This should print:

- table identity
- overall status
- failure stage
- failure reason
- notes
- rescue attempt table

Each attempt row should include:

- `stage`
- `name`
- `considered`
- `ran`
- `succeeded`
- `note`

Purpose:
- explain exactly what the parser tried for one table

### 4. Update `show_table_structure()`

`show_table_structure()` should display processing status before rows, columns, and variables.

Required header fields:

- `processing status`
- `failure_stage`
- `failure_reason`

If the table failed, that should be shown before printing an empty variable or column section.

### 5. Attach processing status to observed-table output

`build_observed_table_one_from_paper_dir()` should load `table_processing_status.json` when present and attach these fields to provenance:

- `processing_status`
- `failure_stage`
- `failure_reason`

If a table failed, printing the observed object should make that clear.

## Data Handling Rules

- match tables by `table_id` first
- fall back to index when needed
- do not infer success from non-empty JSON files alone
- treat `status` in `table_processing_status.json` as the source of truth for process outcome
- treat `table_definitions.json` and `parsed_tables.json` as content artifacts, not status artifacts

## Output Behavior

### Success

Show:
- `status = ok`

### Rescued

Show:
- `status = rescued`
- successful attempts
- final counts so the user sees that recovery worked

### Failed

Show:
- `status = failed`
- `failure_stage`
- `failure_reason`
- attempted rescues
- structural counts such as zero variables, zero usable columns, or zero values

A failed table must be visually distinct from a merely sparse table.

## UI Style

Keep output console-friendly and base-R.

Use:
- one compact data-frame summary for paper-level status
- one readable staged printout for per-table detail

Do not add plotting libraries or a Shiny dependency.

## Required Files

Primary implementation target:

- `R/inspect_paper_outputs.R`

Secondary integration target:

- `R/observed_table_one.R`

Documentation updates:

- `docs/r_visualization.md`

## Non-Goals

- no parser changes
- no schema changes
- no new JSON outputs
- no interactive GUI
- no replacement of current structure-comparison helpers

## Minimum First Version

The minimum acceptable version is:

1. `load_paper_outputs()` loads `parsed_tables.json` and `table_processing_status.json`
2. `summarize_table_processing(paper_dir)` exists
3. `show_table_processing(paper_dir, table_index = 0L)` exists
4. `show_table_structure()` prints status/failure info when available

That is enough for a user to understand what happened during processing of one paper.
