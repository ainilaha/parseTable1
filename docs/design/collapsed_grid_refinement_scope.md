# Collapsed Grid Refinement Scope

## Purpose

Consolidate the duplicated collapsed-grid refinement logic in the PyMuPDF extractor without changing parser behavior or adding new rescue methods.

## Target

Refactor the duplicated rotated/upright collapsed-grid branches in [pymupdf4llm_extractor.py](/Users/robert/Projects/Epiconnector/parseTable1/table1_parser/extract/pymupdf4llm_extractor.py).

Current duplicate areas:

- rotated collapsed-grid refinement
- upright collapsed-grid refinement

Both branches currently:

- build word lines
- trim footer lines using horizontal rules
- rebuild a row grid from lines
- drop empty columns
- compare refined structure to the original grid
- return refined rows plus metadata

## In Scope

- unify the rotated and upright collapsed-grid refinement flow
- keep the logic inside the existing extractor function
- prepare geometry differently by mode, then run one shared inline rebuild block
- preserve current metadata fields and downstream behavior
- preserve current acceptance thresholds unless later testing justifies changing them

## Out Of Scope

- no new extraction algorithms
- no new rescue paths
- no new parser-stage failure logic
- no schema changes
- no CLI changes
- no broader extractor refactor outside this duplicated block

## Design Rules

- do not introduce small single-use helper functions
- keep the shared rebuild flow inline inside the parent function
- treat rotated and upright refinement as one method with two geometry-preparation modes
- keep estimate/model-specific refinement separate for now

## Expected Result

- less duplicated extractor code
- unchanged extractor outputs
- clearer rescue logic for collapsed explicit grids

## Estimated Impact

- likely net reduction: 35 to 50 lines

If a later cleanup also folds the nearby estimate/model rebuild pattern into the same structure, total reduction could reach roughly 55 to 80 lines, but that is not part of this scoped change.
