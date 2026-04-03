# Normalized Column Repair Plan

This document describes a tight normalization-time repair for malformed extracted tables.

## Goal

Repair only the clearest adjacent-column splits before later semantic stages run.

The initial target is:

- split categorical `count` plus `percent` fragments across adjacent columns
- a strongly header-like first body row that becomes obvious after those repairs

This plan is intentionally conservative. It is not a general table-reconstruction engine.

## Inputs

Use only existing deterministic signals:

- `cleaned_rows`
- detected `header_rows` and `body_rows`
- `row_views`
- deterministic variable blocks
- row or variable expected value style
- cell-level value-pattern detection

## Repair Rule

Treat a column as an overflow-fragment candidate only when all of the following are mostly true:

- the candidate column is adjacent to a populated column on its left
- many cells in the candidate column look like parenthesized percent fragments such as `(34.4%)`
- the left column often contains count-only values on the same rows
- those rows belong to a categorical block whose parent variable implies `n (%)`

When confidence is high:

- merge the fragment into the left cell
- move any orphaned header text left if the left header cell is empty
- drop the candidate column if it becomes empty after the repair

## Header Promotion Rule

After repair, re-run header detection.

If the first remaining body row is still near the top and is strongly header-like, allow a conservative promotion into `header_rows`.

Promotion should require strong evidence such as:

- explicit header keywords like `P value`
- multiple threshold or range labels
- mostly text-like cells rather than ordinary row values

## Downstream Effect

This repair is intended to improve:

- column-role detection
- grouped-column semantics
- identification of trailing `p_value` columns

It should not change the core pipeline shape.

## Files

Expected touch points:

- `table1_parser/normalize/pipeline.py`
- `table1_parser/normalize/header_detector.py`
- `table1_parser/heuristics/table_definition_columns.py`
- tests for normalization and table definition

## Success Criteria

After this change, a table with split `n (%)` cells should normalize into:

- one coherent categorical value cell per subgroup column
- cleaner `header_rows`
- more reliable overall/group/stat column inference
