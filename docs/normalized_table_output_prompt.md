Read:

- `AGENTS.md`
- `docs/codex_build_spec.md`
- `docs/design_index.md`

Implement a focused feature to make `NormalizedTable` a persisted, user-visible artifact.

## Goal

Persist normalized tables to disk, make them loadable as formal downstream input, and allow the existing visualization tools to read them.

Do not implement the full `parse` command yet.

## Why

The repository already computes `NormalizedTable` in memory and uses it as input to heuristics and LLM interpretation.

What is missing is:

- a stored normalized artifact for users
- a stable on-disk JSON contract for that artifact
- loader helpers so downstream code can consume saved normalized tables
- visualization support for normalized JSON

## Scope

Implement only:

1. normalized-table JSON persistence
2. normalized-table JSON loading
3. a CLI path for writing normalized output
4. visualization support for normalized JSON
5. tests and docs for the new stored artifact

Do not implement:

- final `ParsedTable` export
- `TableDefinition`
- value extraction
- validation-layer redesign
- full end-to-end parse command

## Recommended Output Layout

Use the existing paper-oriented output root:

```text
outputs/
  papers/
    <paper_stem>/
      extracted_tables.json
      normalized_tables.json
```

`normalized_tables.json` should be a JSON array of direct `NormalizedTable.model_dump(mode="json")` payloads.

Do not wrap the file in trace metadata.

## Files To Add Or Update

Add or update only the small set needed for this feature:

- `table1_parser/cli.py`
- `table1_parser/normalize/__init__.py`
- `table1_parser/normalize/pipeline.py`
- `table1_parser/normalize/interpretation_view.py`
- `R/visualize_table_from_json.R`
- `README.md`
- `docs/parsing_output_design.md`
- tests as needed

You may add one small helper module if useful, for example:

- `table1_parser/normalize/io.py`

## Required Behavior

### 1. Save normalized tables

Add a path that:

- extracts tables from a PDF
- normalizes each extracted table
- writes `normalized_tables.json`

Recommended CLI:

```bash
table1-parser normalize path/to/paper.pdf
```

Also support:

- `--stdout`
- `--outdir`

### 2. Load normalized tables

Add helpers that:

- read `normalized_tables.json`
- validate entries with `NormalizedTable`
- return typed models

This should become the formal input path for later heuristic and parse stages.

### 3. Visualization support

Update the R visualization helper so it can display a normalized-table JSON payload.

It should detect normalized-table-style payloads using fields such as:

- `header_rows`
- `body_rows`
- `row_views`
- `metadata.cleaned_rows`

Use `metadata.cleaned_rows` plus the stored row indices to reconstruct a user-readable table display.

### 4. Keep separation of stages

Do not merge normalized output with heuristic or LLM artifacts.

`NormalizedTable` should remain its own stored stage.

## Tests

Add focused tests for:

- `NormalizedTable` round-trip serialization
- loading normalized JSON into typed models
- CLI writing `normalized_tables.json`
- CLI `--stdout` behavior for normalized output
- visualization helper support for normalized JSON shape

Keep tests small and synthetic.

## Documentation Updates

Update docs to reflect that users can now find:

- `extracted_tables.json`
- `normalized_tables.json`

Be explicit that:

- heuristic and LLM trace outputs still live separately under `outputs/traces/`
- `ParsedTable` export is still not implemented

## Deliverable

After this feature, the repository should support:

```text
PDF -> ExtractedTable -> NormalizedTable
```

with `NormalizedTable` both:

- stored for users and inspection
- reloadable as a formal input to downstream interpretation stages
