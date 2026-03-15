Read:

- AGENTS.md
- docs/codex_build_spec.md

Implement **Phase 4 only**.

## Goal

Build a deterministic heuristic parsing layer that operates on `NormalizedTable`.

Target implementation size: roughly 800–1500 lines including tests.

This phase should add only:

- row classification
- variable grouping
- level detection
- column role detection
- value pattern detection

## Do not implement

Do NOT add:

- LLM code
- prompt code
- validation layer
- final ParsedTable assembly
- end-to-end parse pipeline
- markdown output
- changes to extraction architecture
- major changes to normalization

If a tiny normalization bug fix is absolutely necessary, keep it minimal.

## Files to add

Implement only these modules:

- `table1_parser/heuristics/row_classifier.py`
- `table1_parser/heuristics/variable_grouper.py`
- `table1_parser/heuristics/level_detector.py`
- `table1_parser/heuristics/column_role_detector.py`
- `table1_parser/heuristics/value_pattern_detector.py`

You may add one small schema/helper module if needed, but keep total scope tight.

## Functional requirements

### 1. Row classification
Classify body rows into:

- `variable_header`
- `level_row`
- `continuous_variable_row`
- `section_header`
- `unknown`

Use simple deterministic signals:
- whether trailing cells are empty
- whether trailing cells are numeric/statistical
- whether row text is short/category-like
- whether row follows a likely parent row
- common category labels like Male, Female, Yes, No, Never, Former, Current

Be conservative. Use `unknown` when uncertain.

### 2. Variable grouping
Group rows into candidate variable blocks.

Support:
- one-row continuous variables like `Age, years`
- parent-plus-level blocks like `Sex -> Male/Female`
- section headers that should not become variables

Preserve row indices exactly.

### 3. Level detection
Detect likely levels under a parent variable.

Support examples like:
- Sex → Male, Female
- Education → `<HS`, `High school`, `>High school`
- Smoking status → Never, Former, Current

### 4. Column role detection
Detect likely column roles from header rows.

Supported roles:
- `overall`
- `group`
- `comparison_group`
- `p_value`
- `smd`
- `unknown`

Examples:
- `Overall` → overall
- `P-value` → p_value
- `SMD` → smd

Be conservative.

### 5. Value pattern detection
Classify raw cell values into:
- `count_pct`
- `mean_sd`
- `median_iqr`
- `p_value`
- `n_only`
- `unknown`

Examples:
- `412 (48.2)` → count_pct
- `52.3 (14.1)` → mean_sd
- `43.2 (35.0, 57.1)` → median_iqr
- `<0.001` → p_value
- `412` → n_only

Do not over-parse.

## Tests

Add focused tests only for these heuristics.

Include these examples:

- `Age, years`
- `BMI, kg/m2`
- `Sex`
- `Male`
- `Female`
- `Education`
- `<HS`
- `High school`
- `>High school`
- `Smoking status`
- `Never`
- `Former`
- `Current`
- `Overall`
- `Cases`
- `Controls`
- `P-value`
- `SMD`
- `412 (48.2)`
- `52.3 (14.1)`
- `43.2 (35.0, 57.1)`
- `<0.001`

Include negative cases that should return `unknown`.

## Constraints

- Keep code small and modular
- Do not vendor libraries
- Do not create large fixtures
- Prefer pure functions
- Use type hints everywhere
- Use existing schemas unless a very small new schema is needed

## Deliverable

After this phase, the repo should support:

`NormalizedTable -> heuristic structural interpretation`

Implement Phase 4 only.
