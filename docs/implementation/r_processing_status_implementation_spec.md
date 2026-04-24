# R Processing Status Implementation Spec

## Goal

Implement R-side inspection support for `table_processing_status.json` so users can understand what happened during parsing of each table.

## Scope

Implement only:

- loading `parsed_tables.json` and `table_processing_status.json`
- paper-level processing summary
- table-level processing detail view
- status header in `show_table_structure()`
- optional status provenance in observed-table output

Do not change parser code or JSON schemas.

## Files

- `R/inspect_paper_outputs.R`
- `R/observed_table_one.R`
- `docs/r_visualization.md`
- `man/` docs for any new exported helpers if needed

## Step 1: Load New Artifacts

Update `paper_output_paths()` in `R/inspect_paper_outputs.R` to include:

- `parsed = file.path(paper_dir, "parsed_tables.json")`
- `processing_status = file.path(paper_dir, "table_processing_status.json")`

Update `load_paper_outputs()` to load:

- `parsed_tables`
- `table_processing_status`

Use optional loading for `table_processing_status.json` so older output directories still work.

## Step 2: Add Table Status Resolver

Add internal lookup logic in `R/inspect_paper_outputs.R` to resolve one status record by:

1. `table_id`
2. fallback to table index

This should work the same way existing deterministic/LLM table lookup already works.

No new package dependency.

## Step 3: Add Paper-Level Summary

Add:

- `summarize_table_processing(paper_dir)`

Behavior:
- load paper outputs
- iterate tables by index
- join normalized table, deterministic definition, parsed table, and processing status
- return a base-R data frame
- print it for interactive use

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

Preferred extra columns:

- `table_family`
- `grid_refinement_source`

Rules:
- `variable_count` comes from deterministic `table_definitions.json`
- `usable_column_count` counts non-`unknown` columns
- `value_count` comes from `parsed_tables.json`
- if status file is missing, leave status fields `NA` or empty rather than erroring

## Step 4: Add Table-Level Detail View

Add:

- `show_table_processing(paper_dir, table_index = 0L)`

Behavior:
- print table identity
- print overall `status`
- print `failure_stage`
- print `failure_reason`
- print `notes`
- print attempt table

Attempt table columns:

- `stage`
- `name`
- `considered`
- `ran`
- `succeeded`
- `note`

Rules:
- if no status record exists, print `[No table_processing_status record found]`
- still return the resolved record invisibly when present

## Step 5: Update `show_table_structure()`

Before printing rows/columns/variables, print:

- `processing status`
- `failure_stage`
- `failure_reason`

If status is `failed`, show that prominently before the empty structure sections.

Do not change the existing row/column/variable display format beyond that header addition.

## Step 6: Attach Status To Observed Output

Update `build_observed_table_one_from_paper_dir()` in `R/observed_table_one.R`:

- optionally load `table_processing_status.json`
- resolve the matching table record
- attach to provenance:
  - `processing_status`
  - `failure_stage`
  - `failure_reason`

Do not block object creation if status is missing.

## Step 7: Documentation

Update `docs/r_visualization.md` to include:

- `summarize_table_processing(paper_dir)`
- `show_table_processing(paper_dir, table_index = 0L)`
- note that `load_paper_outputs()` now includes `parsed_tables` and `table_processing_status`

Include one short usage example for each.

## Step 8: Tests

Add or update R smoke tests to cover:

1. `load_paper_outputs()` with `table_processing_status.json`
2. `summarize_table_processing()` returns expected columns
3. `show_table_processing()` prints a failed-table summary
4. `show_table_structure()` includes status header when status exists
5. older paper dirs without `table_processing_status.json` still load

Test fixture rule:

- build repeated `parsed_tables.json` and `table_processing_status.json` payloads through shared reusable test helpers rather than repeating large inline JSON blocks
- keep fixture helpers generic enough to cover both `ok` and `failed` status cases

## Output Rules

- treat `table_processing_status.json` as the source of truth for process outcome
- do not infer success from non-empty `table_definitions.json` or `parsed_tables.json`
- failed tables must be visually distinct from sparse but successful tables
- keep all output base-R and console-friendly

## Non-Goals

- no parser changes
- no new JSON files
- no schema changes
- no plotting layer
- no Shiny UI

## Minimum Deliverable

The implementation is complete when:

1. `load_paper_outputs()` loads `parsed_tables` and optional `table_processing_status`
2. `summarize_table_processing()` works
3. `show_table_processing()` works
4. `show_table_structure()` surfaces failure status
5. docs and tests are updated
