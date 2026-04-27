# RFC 0001: NHANES Extension Layer

Status: Draft

Discussion: TBD

## Summary

This RFC proposes an optional NHANES-specific extension layer for the Table 1 parser.

The core parser should remain focused on extracting and parsing Table 1-style epidemiology tables from PDFs. NHANES-specific functionality should be implemented as a separate downstream layer that consumes existing paper-level and table-level artifacts.

At a high level, the proposed workflow is:

```text
paper outputs + reviewed variables
  -> NHANES study detection
  -> NHANES cycle detection
  -> NHANES variable mapping candidates
  -> user review
```

## Motivation

Many epidemiology papers use NHANES, and mapping reported Table 1 variables back to NHANES source variables would support reproducibility, downstream database queries, and semi-automated reconstruction of analytic cohorts.

The parser already produces useful intermediate artifacts:

- `paper_markdown.md`
- `paper_sections.json`
- `paper_variable_inventory.json`
- `table_contexts/*.json`
- `table_definitions.json`
- `parsed_tables.json`
- optional user/LLM-reviewed variable plausibility artifacts

Those artifacts provide a natural input boundary for NHANES-specific logic.

The main architectural concern is isolation. Parsing Table 1 in epidemiology papers is useful independent of NHANES, so NHANES assumptions should not leak into extraction, normalization, table-definition building, parsed-table assembly, or generic LLM review.

## Non-Goals

This RFC does not propose changing the core parse pipeline:

```text
PDF -> ExtractedTable -> NormalizedTable -> TableDefinition -> ParsedTable
```

This RFC does not propose:

- embedding NHANES-specific heuristics in generic extraction, normalization, or parsing modules
- making NHANES detection part of `table1-parser parse`
- automatically rewriting deterministic variables based on NHANES metadata
- silently accepting NHANES variable mappings without human review
- solving full analytic-cohort reconstruction in the first implementation
- requiring all future data-source-specific logic to use NHANES conventions

## Proposed Architecture

Add a separate NHANES package namespace, for example:

```text
table1_parser/nhanes/
```

The NHANES layer should consume existing persisted outputs rather than rerunning or modifying the core parser internals.

Proposed stages:

1. Detect whether the paper used NHANES.
2. Identify reported NHANES years, cycles, or release periods.
3. Normalize detected cycles into a stable representation.
4. Accept a reviewed list of paper variables as mapping input.
5. Load or query NHANES metadata for relevant cycles.
6. Produce candidate NHANES variable mappings.
7. Expose candidate mappings for user review in R or JSON.

Conceptually:

```text
Core parser artifacts
  -> NHANES detector
  -> NHANES study context

NHANES study context + reviewed paper variables + NHANES metadata
  -> NHANES mapper
  -> mapping candidates
```

The NHANES code should be optional and should not be imported by core parser modules unless explicitly requested by an NHANES command or API.

## Proposed Artifacts

### `nhanes_study_context.json`

Proposed path:

```text
outputs/papers/<paper_stem>/nhanes_study_context.json
```

Purpose:

- record whether NHANES appears to be the primary data source
- distinguish primary use from background-only mentions
- preserve text evidence for NHANES detection
- record detected years, cycles, and ambiguity

Candidate fields:

- `paper_id`
- `uses_nhanes`
- `use_classification`
- `confidence`
- `detected_cycles`
- `detected_year_ranges`
- `evidence`
- `notes`

### `nhanes_variable_mapping_candidates.json`

Proposed path:

```text
outputs/papers/<paper_stem>/nhanes_variable_mapping_candidates.json
```

Purpose:

- record candidate NHANES variables for each reviewed paper variable
- preserve ranking signals and cycle availability
- avoid committing to a single mapping without review

Candidate fields:

- `paper_id`
- `cycles`
- `paper_variables`
- `mapping_candidates`
- `metadata_source`
- `notes`

Each mapping candidate should preserve:

- paper variable identity
- candidate NHANES variable name
- NHANES component/table
- NHANES label or description
- cycle availability
- score
- evidence or rationale
- ambiguity notes

## CLI/API Sketch

The NHANES workflow should be exposed through optional commands rather than through `parse`.

Possible CLI commands:

```bash
table1-parser nhanes-detect path/to/paper.pdf
```

or:

```bash
table1-parser nhanes-detect outputs/papers/<paper_stem>
```

Possible later mapping command:

```bash
table1-parser nhanes-map outputs/papers/<paper_stem>
```

Possible combined review command:

```bash
table1-parser nhanes-review outputs/papers/<paper_stem>
```

Open design choice:

- commands may accept a PDF path and build missing core outputs
- commands may require an existing paper output directory to enforce the downstream boundary

The second option is cleaner architecturally because it makes NHANES analysis explicitly downstream of parsing.

## R Workflow Sketch

R helpers should focus on review and inspection, not hidden mutation.

Possible R functions:

```r
source("R/inspect_paper_outputs.R")
source("R/nhanes_inspection.R")

outputs <- load_paper_outputs("outputs/papers/example")
show_nhanes_study_context("outputs/papers/example")
nhanes_mapping_candidates_df("outputs/papers/example")
show_nhanes_mapping_candidates("outputs/papers/example")
```

The R display should make it easy to compare:

- reviewed paper variable label
- deterministic variable type
- Table 1 levels, when present
- candidate NHANES variable name
- candidate NHANES label
- component/table
- cycle availability
- score and notes

The user should be able to identify unresolved or low-confidence mappings without reading raw JSON.

## Open Questions

1. Should NHANES detection accept a PDF path, a paper output directory, or both?
2. What counts as strong evidence that NHANES is the primary data source rather than a background citation?
3. How should complex survey cycles be represented when papers use broad ranges such as "1999-2018"?
4. Should the first implementation use a local NHANES metadata cache, an online source, or both?
5. What is the canonical reviewed-variable input to the mapping step?
6. Should LLM assistance be allowed for NHANES detection, variable mapping, both, or neither?
7. How should mappings represent derived variables that do not correspond to a single NHANES source variable?
8. How should mappings represent variables assembled from multiple NHANES components?
9. What confidence threshold should trigger manual review warnings?
10. Should NHANES mapping artifacts be considered stable downstream contracts or inspection artifacts at first?

## Alternatives Considered

### Add NHANES logic directly to `parse`

Rejected for now.

This would make NHANES a first-class concern in the generic Table 1 parser and would blur the boundary between paper parsing and data-source-specific interpretation.

### Add NHANES heuristics inside `TableDefinition`

Rejected for now.

`TableDefinition` should describe variables reported in the table. It should not know whether those variables came from NHANES, UK Biobank, Medicare claims, or another source.

### Treat NHANES mapping as an LLM-only task

Rejected for now.

LLM assistance may be useful later, but the first design should preserve explicit NHANES metadata, cycle availability, and deterministic candidate ranking wherever possible.

### Use a single final NHANES mapping per paper variable

Rejected for now.

Many paper variables are derived, renamed, categorized, or ambiguously labeled. The safer initial output is a ranked candidate list that requires user review.

### Build a generic data-source mapping layer first

Deferred.

A generic data-source abstraction may be useful later, but NHANES has specific cycle, component, and metadata conventions. A focused NHANES extension is a better first step if it remains isolated from the core parser.

