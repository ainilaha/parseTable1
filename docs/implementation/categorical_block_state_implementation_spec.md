# Categorical Block State Implementation Spec

## Goal

Implement minimal categorical-block state and narrow `binary_variable_row` detection using the existing deterministic heuristics flow.

## Files

- `table1_parser/heuristics/models.py`
- `table1_parser/heuristics/row_classifier.py`
- `table1_parser/heuristics/variable_grouper.py`
- `table1_parser/heuristics/table_definition_rows.py`
- `tests/test_heuristics.py`

## Constraints

- do not add a new parser stage
- do not change output schemas
- do not add small single-use helpers
- keep the change limited to deterministic heuristics

## Step 1: Add the row class

In `models.py`, add:

- `binary_variable_row`

This is a structural classifier output, not a new schema object.

## Step 2: Track categorical block state

In `row_classifier.py`, keep block-local state during `classify_rows(...)`:

- active parent row
- accepted level count
- whether accepted levels have established an indentation requirement

Required behavior:

- `variable_header` opens a candidate block
- first accepted level increments the count
- if that first accepted level is indented, later levels must also be indented
- if a later row breaks the established level pattern, stop classifying it as `level_row`

## Step 3: Add narrow `binary_variable_row` detection

Still in `row_classifier.py`, classify a row as `binary_variable_row` only when:

- it is top-level relative to the active parent
- it has populated non-stat value cells
- it matches count/percent-like output
- it does not look continuous
- it is not a strong child level of the active categorical parent

Level detection must continue to win when parent evidence is strong, so rows under `Smoking` stay as levels.

## Step 4: Group `binary_variable_row` as a standalone variable

In `variable_grouper.py`, treat `binary_variable_row` like a one-row variable block rather than a child level.

## Step 5: Map the row class to semantic output

In `table_definition_rows.py`, map `binary_variable_row` to:

- `variable_type = "binary"`

Use the existing one-row variable flow rather than introducing a new schema.

## Step 6: Add focused regression tests

In `tests/test_heuristics.py`, add or extend tests for:

- `PIR` not remaining under `Ethnicity`
- `Alcohol consumption` stopping after its two levels
- at least one standalone binary row in the `metabolic` pattern being classified as `binary_variable_row`
- `Smoking -> Never / Former / Current` remaining a categorical parent with levels

## Validation

Run:

```bash
pytest tests/test_heuristics.py -q
```

Then re-parse:

```bash
python3 -m table1_parser.cli parse /Users/robert/Projects/Epiconnector/metabolic.pdf --no-llm-semantic
```

Check:

- `outputs/papers/metabolic/table_definitions.json`
- `outputs/papers/metabolic/parsed_tables.json`

## Minimum Success Criteria

- `PIR` is no longer attached to `Ethnicity`
- `Alcohol consumption` no longer absorbs later top-level rows
- at least one correct standalone binary row is emitted as its own variable
- `Smoking` remains correct
