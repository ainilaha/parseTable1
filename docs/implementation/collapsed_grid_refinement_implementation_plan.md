# Collapsed Grid Refinement Implementation Plan

## Goal

Remove the duplicated rotated/upright collapsed-grid refinement logic in the extractor while keeping behavior unchanged.

## Files

- `table1_parser/extract/pymupdf4llm_extractor.py`
- `tests/test_extraction.py`

## Constraints

- do not add new rescue methods
- do not add small single-use helpers
- keep logic inline inside `_refine_explicit_table_candidate_grid(...)`
- do not change schemas, CLI behavior, or output metadata names

## Steps

1. Identify the duplicated block in `_refine_explicit_table_candidate_grid(...)`
   - rotated collapsed-grid branch
   - upright collapsed-grid branch

2. Replace those two branches with one shared inline flow
   - first decide refinement mode: `rotated` or `upright`
   - prepare one working geometry set for that mode:
     - words
     - chars
     - rules
     - bbox
     - horizontal rules
     - output metadata values

3. Run one shared rebuild sequence
   - `build_word_lines(...)`
   - footer trim using the mode-specific horizontal rules
   - `build_row_grid_from_lines(...)`
   - drop empty columns
   - apply the current acceptance threshold for that mode

4. Preserve current outputs
   - rotated result must still return:
     - `grid_refinement_source = "rotated_word_positions_with_rules"`
     - `geometry_coordinate_frame = "table_local_rotated_normalized"`
   - upright result must still return:
     - `grid_refinement_source = "collapsed_explicit_grid_word_positions"`
     - `geometry_coordinate_frame = "page"`

5. Leave the estimate/model-header refinement branch unchanged
   - do not fold that branch into this change

6. Update tests
   - keep the current upright collapsed-grid regression test
   - keep the rotated collapsed-grid regression test
   - verify both modes still refine and preserve their expected metadata

## Validation

Run:

```bash
pytest tests/test_extraction.py -q
```

## Expected Outcome

- same extractor behavior
- clearer control flow
- about 35 to 50 lines removed
