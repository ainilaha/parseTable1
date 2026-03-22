# Parsing Process Overview

This project parses Table 1-style epidemiology tables in stages. The goal is to keep each stage small, inspectable, and reliable.

## Intended Process

The intended pipeline is:

```text
PDF -> ExtractedTable -> NormalizedTable -> ParsedTable
```

In plain terms:

- `ExtractedTable` is what the PDF extraction layer found
- `NormalizedTable` is the cleaned and organized version used for interpretation
- `ParsedTable` is the final structured result with variables, levels, columns, and values

## What `NormalizedTable` Means

A `NormalizedTable` is the intermediate representation between raw extraction and final parsing.

It keeps the table structure, but makes it easier to interpret by:

- separating header rows from body rows
- cleaning cell text
- preserving raw row content
- computing row-level signals such as:
  - whether a row has trailing values
  - whether the first cell looks like a variable label
  - indentation level when it can be inferred

It does not yet decide the final meaning of the table.

For example, a `NormalizedTable` can represent:

- which rows are likely headers
- what the cleaned rows look like
- which rows belong to the body

But it does not yet fully decide:

- which row starts a variable
- which rows are levels under that variable
- what each value means numerically

## What Happens After Normalization

Later stages use the `NormalizedTable` to make progressively stronger interpretations:

- heuristics classify rows and group likely variables
- optional LLM interpretation refines ambiguous structure
- validation checks that the interpretation is consistent with the real table
- final assembly produces a `ParsedTable`

## Why This Separation Matters

This separation keeps the parser safer and easier to debug.

- extraction errors can be inspected separately
- normalization can preserve the original table while cleaning it
- heuristics can stay deterministic
- LLM use can be limited to ambiguity instead of raw extraction
- final parsed output can be validated before it is accepted

## For Users

If you are looking at parser outputs:

- raw extraction output answers: "What table did the PDF extractor recover?"
- normalized output answers: "What cleaned table structure will the parser reason over?"
- parsed output answers: "What variables, levels, columns, and values did the system finally infer?"
