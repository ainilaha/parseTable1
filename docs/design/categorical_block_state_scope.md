# Categorical Block State Scope

## Purpose

Add minimal block-level state to deterministic row classification so a categorical parent is not treated as an open-ended sequence of levels.

Also add a narrow positive path for standalone `one_row_binary` rows such as `Healthy diet`.

## Problem

Current row classification is too local. It knows the previous row and immediate row cues, but it does not know:

- whether a categorical parent has already found valid levels
- how many levels have been accepted
- whether accepted levels are indented or flush-left
- when a later row breaks that pattern

This causes rows like `PIR` and `Healthy diet` to be absorbed into the preceding categorical block.

## Design Goals

- track minimal categorical-block state during deterministic row classification
- close a categorical block when later rows break the established level pattern
- add a structural row class for standalone one-row binary summaries
- detect at least one, and ideally all appropriate, `one_row_binary` rows in `metabolic`
- keep the change inside the existing heuristics flow

## Proposed State

Track during `classify_rows(...)`:

- `active_parent_row_view`
- `active_parent_level_count`
- `active_parent_requires_indented_levels`

This is the minimum state for the first implementation.

## Row Classes

Existing classes stay in place.

Add:

- `binary_variable_row`

Meaning:

- top-level row
- populated non-stat value cells
- structurally complete on its own
- value pattern is count/percent-like rather than continuous

## Core Rules

### 1. Strong categorical parent opens a block

When a row is classified as `variable_header`, open a candidate categorical block and initialize:

- `active_parent_level_count = 0`
- `active_parent_requires_indented_levels = FALSE`

### 2. First accepted level validates the block

When a following row is accepted as `level_row`:

- increment `active_parent_level_count`
- if the level is more indented than the parent, set `active_parent_requires_indented_levels = TRUE`

### 3. Indented blocks stay indented

Once `active_parent_requires_indented_levels = TRUE`, later rows must not continue that block as `level_row` unless they remain more indented than the parent.

### 4. Pattern breaks close the block

If a later row no longer matches the accepted level pattern, stop treating it as `level_row` and let it fall through to:

- `binary_variable_row`
- `continuous_variable_row`
- `variable_header`
- `unknown`

### 5. Standalone one-row binary detection

A row is eligible for `binary_variable_row` when it:

- is top-level relative to the active parent
- has populated non-stat value cells
- looks like `count_pct` or count-like binary output
- does not look continuous
- is not a strong child level of the active categorical parent

## Expected Effect On `metabolic`

After this change:

- `Ethnicity` should stop at its true levels
- `PIR` should not remain under `Ethnicity`
- `Alcohol consumption` should stop after `Binge drinking` and `Non-binge drinking`
- at least one appropriate standalone binary row should become its own variable
- ideally `Healthy diet`, `Regular physical activity`, `Adequate sleep duration`, and `Less sedentary behaviors` should all be detected as standalone binary variables

This scope does not attempt to solve the later lipid and HbA1c continuous-summary rows.

## Implementation Targets

- `table1_parser/heuristics/models.py`
- `table1_parser/heuristics/row_classifier.py`
- `table1_parser/heuristics/variable_grouper.py`
- `table1_parser/heuristics/table_definition_rows.py`
- `tests/test_heuristics.py`

## Constraints

- no new parser stage
- no output-schema changes
- keep the logic inside existing deterministic heuristics
- avoid small single-use helpers

## Minimum Deliverable

1. Categorical block state is tracked during row classification.
2. Later rows cannot continue an indented categorical block unless they stay indented.
3. `binary_variable_row` exists as a classifier output.
4. At least one correct standalone binary row is detected in `metabolic`.
5. Regression tests cover both categorical boundary stopping and one-row-binary detection.
