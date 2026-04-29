# Parse Quality Reports Implementation Spec

## Goal

Implement `parse_quality_reports.json` as a normal `table1-parser parse` artifact.

Design reference:

- `docs/design/parse_quality_reports_artifact.md`

The implementation must be observability-only.
It must not change extraction, normalization, table definitions, parsed tables, processing status, LLM behavior, or Table 1 continuation merging.

## Files To Update

Core Python:

- `table1_parser/cli.py`

R inspection:

- `R/inspect_paper_outputs.R`

Tests:

- `tests/test_cli.py`
- `tests/test_r_inspection.py`
- existing `tests/test_diagnostics.py` should remain focused unit coverage

Docs:

- `docs/design/parsing_output_design.md`
- `docs/design/paper_parse_walkthrough.md`
- `docs/r_visualization.md`

No schema change is expected because `ParseQualityReport`, `ParseQualitySummary`, and `DiagnosticItem` already exist in `table1_parser/diagnostics.py`.

## Python Implementation Steps

### 1. Import Existing Diagnostic Helpers

In `table1_parser/cli.py`, import:

- `ParseQualityReport`
- `build_parse_quality_report`
- `classify_rows`
- `group_variable_blocks`
- `detect_column_roles`

Use existing modules rather than duplicating heuristic logic.

### 2. Extend `PaperParseArtifacts`

Add:

```python
parse_quality_reports: list[ParseQualityReport]
```

Keep the field near the other table-level deterministic artifacts.

### 3. Build Reports During Parse

In `_build_paper_parse_artifacts(...)`, after `normalized_tables` exists, build one report per normalized table.

For each table:

```python
row_classifications = classify_rows(table)
variable_blocks = group_variable_blocks(table, classifications=row_classifications)
column_roles = detect_column_roles(table)
report = build_parse_quality_report(
    table,
    row_classifications,
    variable_blocks,
    column_roles,
    extracted_table=matching_extracted_table,
    source_identifier=pdf_path,
)
```

The matching extracted table can be selected by list position because `normalize_extracted_tables(...)` preserves extracted-table order.
If the lengths ever differ, pass `None` rather than failing parse.

Implementation constraint:

- do not reuse these computed classifications to change the main parser output in this change
- do not make parse fail because a report contains warnings or errors

### 4. Serialize Reports

Add a helper only if consistent with existing CLI style.
Otherwise write inline in `_write_parse_outputs(...)`:

```python
parse_quality_output_path.write_text(
    json.dumps([report.model_dump(mode="json") for report in artifacts.parse_quality_reports], indent=2) + "\n",
    encoding="utf-8",
)
```

Output path:

```text
outputs/papers/<paper_stem>/parse_quality_reports.json
```

### 5. Preserve Existing Outputs

The parse command should continue writing all existing files:

- `extracted_tables.json`
- `normalized_tables.json`
- `table1_continuation_groups.json`
- `merged_table1_tables.json`
- `table_profiles.json`
- `table_definitions.json`
- `parsed_tables.json`
- `table_processing_status.json`
- paper context artifacts

`parse_quality_reports.json` is additive.

## R Implementation Steps

### 1. Load The Artifact

In `paper_output_paths(...)`, add:

```r
parse_quality_reports = file.path(paper_dir, "parse_quality_reports.json")
```

In `load_paper_outputs(...)`, add:

```r
parse_quality_reports = read_optional_json(paths$parse_quality_reports)
```

### 2. Add Summary Counts

Update `summarize_table_processing(...)` so each table row can include parse-quality counts when available:

- `quality_table_warning_count`
- `quality_table_error_count`
- `quality_row_warning_count`
- `quality_row_error_count`
- `quality_column_warning_count`
- `quality_column_error_count`

If no report is present for a table, return `NA_integer_` for these fields.

Reports should be matched by `table_id` when possible, falling back to list position.

### 3. Add Focused Inspection Helper

Add:

```r
show_parse_quality <- function(paper_dir, table_index = 0L)
```

It should:

- load paper outputs
- select the report by table index
- print table ID and summary counts
- print table diagnostics
- print row diagnostics
- print column diagnostics

Use simple base-R data frames.
Keep this helper read-only.

Suggested printed columns:

- `severity`
- `code`
- `message`
- `row_idx`
- `col_idx`

Only include `row_idx` or `col_idx` when relevant.

## Tests

### CLI Tests

Update the existing parse-output CLI test in `tests/test_cli.py`:

- assert `parse_quality_reports.json` exists
- assert it is valid JSON
- assert it is an empty list when the mocked parse has no tables, or has one report per mocked normalized table if the test fixture creates normalized tables

If the current CLI fixture bypasses real extraction/normalization, keep the expected output consistent with that fixture.

### R Inspection Tests

Update `tests/test_r_inspection.py` sample paper output fixture:

- write a minimal `parse_quality_reports.json`
- include at least one table diagnostic and one column diagnostic

Add or extend a test to verify:

- `load_paper_outputs(...)` loads `parse_quality_reports`
- `summarize_table_processing(...)` includes quality warning/error columns
- `show_parse_quality(...)` prints diagnostic code text, including a column diagnostic

### Diagnostics Unit Tests

Do not move or duplicate existing diagnostic logic tests.
`tests/test_diagnostics.py` remains the direct unit-test coverage for `build_parse_quality_report(...)`.

## Documentation Updates

### `docs/design/parsing_output_design.md`

Add `parse_quality_reports.json` to the output layers table.

Add a short section describing:

- canonical type: `ParseQualityReport`
- purpose: deterministic row/column/value-pattern diagnostics
- relationship to `table_processing_status.json`
- non-goal: does not alter parse outputs

### `docs/design/paper_parse_walkthrough.md`

Add a step near the deterministic table pipeline:

```text
normalized tables -> row/column diagnostics -> parse_quality_reports.json
```

Clarify that the artifact is written for inspection and does not change parse behavior.

### `docs/r_visualization.md`

Add:

- `show_parse_quality(paper_dir, table_index = 0L)`
- note that `load_paper_outputs(...)` includes `parse_quality_reports`

## Validation Commands

Run focused tests:

```bash
python3 -m pytest tests/test_diagnostics.py tests/test_cli.py tests/test_r_inspection.py -q
```

Run the full suite:

```bash
python3 -m pytest
```

Run at least one real parse and inspect the artifact:

```bash
table1-parser parse /Users/robert/Projects/Epiconnector/testpapers/papers_from_johnny/fld.pdf
```

Then verify:

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("outputs/papers/fld/parse_quality_reports.json")
reports = json.loads(path.read_text())
print(len(reports))
print(reports[0]["table_id"])
print(reports[0]["summary"])
print(reports[0]["column_diagnostics"][:3])
PY
```

R inspection smoke test:

```bash
Rscript -e 'source("R/inspect_paper_outputs.R"); show_parse_quality("outputs/papers/fld", table_index = 0L)'
```

## Acceptance Criteria

- `table1-parser parse` writes `parse_quality_reports.json`.
- The file contains one report per normalized table.
- Existing parser outputs remain unchanged except for the additive artifact.
- R inspection loads and displays parse-quality diagnostics.
- Column diagnostics are visible from R.
- Focused and full test suites pass.

## Explicit Non-Changes

Do not:

- modify `ParsedTable` schema
- modify `TableDefinition` schema
- change `table_processing_status.json` semantics
- fail parse based on diagnostics
- consolidate Table 1 continuations
- add LLM calls
- add paper-specific diagnostic rules
