Read:

AGENTS.md
docs/design/codex_build_spec.md

Implement Phase 3 only.

Goal: build the normalization layer that converts ExtractedTable into NormalizedTable.

Do not implement heuristic parsing, variable grouping, column interpretation, value extraction, or LLM integration yet.

## Phase 3 tasks

Implement these modules:

- table1_parser/normalize/cleaner.py
- table1_parser/normalize/text_normalizer.py
- table1_parser/normalize/header_detector.py
- table1_parser/normalize/row_signature.py
- table1_parser/normalize/interpretation_view.py

You may also add a small pipeline helper if useful.

## Required behavior

Given an ExtractedTable, create a NormalizedTable that:

- preserves row and column order
- cleans whitespace
- preserves raw cell text
- derives normalized first-column text
- derives alpha-only first-column text
- identifies likely header rows
- computes row signatures for body rows

## Cleaning requirements

Implement deterministic text cleaning:

- collapse repeated whitespace
- strip surrounding whitespace
- normalize common dash variants
- preserve original text separately where needed
- do not discard raw values

## Text normalization requirements

For the first column, compute:

- raw text
- normalized text
- alpha-only text

Examples:
- "Age, years" -> normalized "Age years"
- "BMI, kg/m2" -> normalized "BMI kg m2"
- "<HS" -> raw preserved; alpha-only may be "HS"

Do not destructively overwrite original strings.

## Header detection

Implement simple heuristics for likely header rows using:

- top rows of the table
- text-heavy rows
- low numeric density
- presence of words like:
  - overall
  - p-value
  - total
  - n
  - %

Return header_rows and body_rows.

## Row signatures

For each body row, compute:

- row_idx
- raw_cells
- first_cell_raw
- first_cell_normalized
- first_cell_alpha_only
- nonempty_cell_count
- numeric_cell_count
- has_trailing_values
- indent_level if inferable, else None
- likely_role only if confidence is high, else None

Do not implement full row classification yet.

## interpretation_view.py

Add a helper that converts a NormalizedTable into a compact dict suitable for later LLM use, but do not add any LLM code yet.

## Tests

Add tests for:

- whitespace cleaning
- text normalization
- alpha-only conversion
- header detection
- row signature generation
- ExtractedTable -> NormalizedTable conversion

## CLI

Do not expand the parse command yet unless needed for debugging.
If useful, add a temporary dev-only way to print normalized output, but keep it minimal.

## Constraints

- Do not vendor libraries
- Keep this phase focused
- Total added code should stay modest
- Preserve strict module separation

## Deliverable

After Phase 3, the codebase should support:

ExtractedTable -> NormalizedTable

with tested normalization behavior.
