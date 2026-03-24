# Multitable Routing Implementation Plan

This document turns the multitable routing spec into an implementation sequence that can be delivered incrementally.

It is intended to follow:

- `docs/multitable_architecture_spec.md`
- `docs/parsing_output_design.md`

The immediate goal is not to solve all table families at once. The first goal is to stop applying Table 1-oriented semantics and unnecessary LLM work to tables that are obviously estimate-result tables.

## Goal

Implement mixed-table routing after normalization so the parser can:

- recognize descriptive characteristic tables
- recognize estimate-result tables
- skip semantic LLM interpretation when a table family does not need it
- preserve explicit routing evidence for debugging

This phase should create the routing layer first. Family-specific estimate parsing can then be added on top of that route decision.

## Target Pipeline

The long-term target is:

```text
PDF
-> ExtractedTable
-> NormalizedTable
-> TableProfile
-> family-specific definition
-> family-specific parsed output
```

The first implementation step should insert `TableProfile` without requiring the full estimate-table parser to exist yet.

## Phase Breakdown

Recommended implementation order:

1. `TableProfile` schema and deterministic routing
2. CLI persistence of `table_profiles.json`
3. LLM gating driven by `TableProfile.should_run_llm_semantics`
4. rename current Table 1 path conceptually to `descriptive_characteristics`
5. add estimate-table definition and parsed output later

This keeps the first change small and useful.

## Phase A: `TableProfile`

### Scope

Implement a deterministic routing artifact that classifies each normalized table into:

- `descriptive_characteristics`
- `estimate_results`
- `unknown`

### Output

Add a new canonical schema:

- `table1_parser/schemas/table_profile.py`

Add a new persisted file:

- `parseTable1.out/papers/<paper_stem>/table_profiles.json`

The file should be a JSON array of direct `TableProfile.model_dump(mode="json")` payloads.

### Required Fields

Each `TableProfile` should include:

- `table_id`
- `title`
- `caption`
- `table_family`
- `should_run_llm_semantics`
- `family_confidence`
- `evidence`
- `notes`

### Recommended Modules

- `table1_parser/schemas/table_profile.py`
- `table1_parser/heuristics/table_profile.py`
- `table1_parser/validation/table_profile.py`

### Deterministic Evidence Signals

Use normalized-table, title, and caption cues only.

#### Descriptive-characteristics cues

- multiple body rows that look like row variables and level rows
- value patterns dominated by:
  - `count_pct`
  - `mean_sd`
  - `median_iqr`
  - `n_only`
- column headers with:
  - `overall`
  - subgroup names
  - `p_value`
- title/caption terms such as:
  - `characteristics`
  - `baseline`
  - `clinical characteristics`
  - `demographic`

#### Estimate-results cues

- many cells that resemble:
  - estimate + CI
  - p-values
  - separate estimate and CI columns
- column labels such as:
  - `hazard ratio`
  - `odds ratio`
  - `relative risk`
  - `95% CI`
  - `adjusted`
  - `unadjusted`
  - `model 1`
  - `model 2`
- title/caption terms such as:
  - `association`
  - `regression`
  - `multivariable`
  - `cox`
  - `logistic`
  - `hazard ratio`
  - `odds ratio`

#### Unknown cues

- weak or conflicting evidence
- no stable dominance of descriptive or estimate-result patterns

### Decision Rule

The first implementation should be conservative:

- require multiple pieces of consistent evidence before labeling `estimate_results`
- default to `descriptive_characteristics` only when the current Table 1-style heuristics clearly fit
- otherwise fall back to `unknown`

### Validation

Validation should ensure:

- allowed family labels only
- `should_run_llm_semantics` matches family policy
- confidence stays between 0 and 1

## Phase B: LLM Gating

### Scope

Use `TableProfile.should_run_llm_semantics` to decide whether the current semantic LLM stage runs for a table.

### Initial Policy

- `descriptive_characteristics`
  - `should_run_llm_semantics = True`
- `estimate_results`
  - `should_run_llm_semantics = False`
- `unknown`
  - `should_run_llm_semantics = False`

This policy should be explicit in routing code, not scattered across CLI conditionals.

### CLI Behavior

`table1-parser parse` should:

- build `TableProfile` for each normalized table
- write `table_profiles.json`
- run semantic LLM only for profiles where `should_run_llm_semantics` is true

For now:

- existing `table_definitions.json` and `parsed_tables.json` may still be written for all tables
- but semantic LLM should be skipped for routed estimate tables

This is already useful because it avoids unnecessary timeouts and cost on multi-table papers.

## Phase C: Family Naming Cleanup

### Scope

Rename the current mental model from "Table 1 parser" to `descriptive_characteristics` in code comments, docs, and future module naming where practical.

### Important Constraint

This does not require a risky large-scale rename in one commit.

Near term:

- keep current modules working
- update docs and future new modules to use the broader family name

This avoids churn while still correcting the architecture.

## Phase D: `EstimateTableDefinition`

### Scope

After routing is stable, add a value-free semantic schema for estimate-result tables.

### Output

Add:

- `table1_parser/schemas/estimate_table_definition.py`
- `parseTable1.out/papers/<paper_stem>/estimate_table_definitions.json`

### Focus

Infer at least:

- metric type
- CI style
- term rows
- model columns
- p-value columns
- adjustment labels

### Recommended Modules

- `table1_parser/schemas/estimate_table_definition.py`
- `table1_parser/heuristics/estimate_table_rows.py`
- `table1_parser/heuristics/estimate_table_columns.py`
- `table1_parser/heuristics/estimate_table_builder.py`
- `table1_parser/validation/estimate_table_definition.py`

### Important Constraint

Do not introduce LLM dependence here.

This phase should stay deterministic-first and table-text-first.

## Phase E: `ParsedEstimateTable`

### Scope

After value-free estimate semantics are stable, add the final parsed estimate output.

### Output

Add:

- `table1_parser/schemas/parsed_estimate_table.py`
- `parseTable1.out/papers/<paper_stem>/parsed_estimate_tables.json`

### Parsing Goals

Parse:

- estimate
- CI lower and upper bounds
- p-value
- model label
- term label

### Important Constraint

Do not reuse `ParsedTable` if it creates awkward or misleading field semantics.

Estimate-result tables should have a dedicated final schema.

## Phase F: Future Model-Context Interpretation

### Scope

Later, add a separate optional stage for understanding the model itself from paper context.

This stage should answer:

- what model family produced the estimates
- what outcome the table refers to
- what `Adjusted` or `Model 2` means
- what covariates are likely included

### Important Constraint

This should be separate from numeric parsing.

The estimate parser should work without it.

### Suggested Future Artifact

- `estimate_model_contexts/*.json`

## CLI Plan

### Immediate CLI additions

After Phase A and B, `table1-parser parse` should write:

- `extracted_tables.json`
- `normalized_tables.json`
- `table_profiles.json`
- `table_definitions.json`
- `parsed_tables.json`
- `paper_markdown.md`
- `paper_sections.json`
- `table_contexts/*.json`

with semantic LLM calls skipped for tables whose profile says not to run them.

### Later CLI additions

After estimate-table phases are implemented, `parse` should also write:

- `estimate_table_definitions.json`
- `parsed_estimate_tables.json`

These may be empty arrays when no estimate-result tables are present.

## Tests

### Phase A / B tests

Add tests for:

- schema validation of `TableProfile`
- deterministic classification into:
  - `descriptive_characteristics`
  - `estimate_results`
  - `unknown`
- `should_run_llm_semantics` policy
- `parse` writing `table_profiles.json`
- semantic LLM skipping estimate-result tables

### Suggested fixtures

Use:

- current synthetic descriptive tables
- at least one handcrafted normalized estimate-result fixture
- mixed-paper examples such as the Nephro paper layout

### Later estimate-table tests

Add tests for:

- metric detection
- CI-style detection
- model-column detection
- estimate parsing
- validation of row/column references

## Success Criteria

Phase A and B are successful when:

- a mixed paper produces a `table_profiles.json` file
- Table 1 and Table 2-style characteristic tables route to `descriptive_characteristics`
- obvious estimate-result tables route to `estimate_results`
- semantic LLM calls are skipped for `estimate_results`
- existing descriptive-table outputs still work

The later phases are successful when:

- estimate-result tables receive their own explicit semantic and parsed outputs
- model-result parsing no longer depends on Table 1-style row/level assumptions
- future model-context interpretation can be added without changing deterministic numeric parsing
