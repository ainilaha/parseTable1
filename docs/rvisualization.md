# R Visualization Instructions

Implement one small R visualization helper only.

## Goal

Create a simple R function that reads one JSON file produced by the parser and displays the reconstructed table as a human-readable table.

This is only for human visual inspection.

Do not implement comparison logic.
Do not implement diffs.
Do not read two files.
Do not redesign the parser.

## Location

Put the code in:

R/visualize_table_from_json.R

## Required function

Implement one main function:

`visualize_table_from_json(json_path)`

## Behavior

The function should:

1. read a single JSON file
2. inspect the JSON structure already produced by the parser
3. reconstruct the parsed table into a simple human-readable tabular form
4. print the table clearly for a human to inspect

The goal is to make it easy to see:
- variable rows
- level rows
- column headers
- values

## Input assumptions

Use the fields that already exist in the JSON file.

Use the real field names already present in the repo output, such as whatever is available among:
- title
- caption
- header rows
- body rows
- variables
- levels
- columns
- values

Do not invent a new JSON schema unless absolutely necessary.

## Output requirements

The function should produce a simple readable table display using base R only.

Use base R objects such as:
- list
- matrix
- data.frame

If helpful, represent level rows visually under their parent variable by indenting the displayed row label with spaces.

Example idea:
- `Age`
- `Sex`
- `  Male`
- `  Female`

The goal is readability for a human.

## Important constraints

- Do NOT use tidyverse
- Do NOT use tibble
- Do NOT use dplyr
- Do NOT use purrr
- Do NOT force use of the `table1` package

The `table1` package is primarily designed for generating summaries from subject-level data.
Here we already have summarized parsed table structure in JSON.
So the code should reconstruct and print the table directly.

## Script behavior

Also make the file runnable from the command line like:

Rscript R/visualize_table_from_json.R path/to/file.json

When run this way, it should:
1. read the JSON file
2. call `visualize_table_from_json()`
3. print the reconstructed table

## Optional small enhancement

If easy, print the title or caption above the table.

## Deliverable

After this change, I should be able to run:

Rscript R/visualize_table_from_json.R some_parser_output.json

and see a readable reconstructed table for human inspection.

Target size: roughly 60–120 lines of R code.
