# R Visualization

The repository includes small base-R helpers for visually inspecting parser JSON output.

File:

- [`R/visualize_table_from_json.R`](../R/visualize_table_from_json.R)
- [`R/inspect_paper_outputs.R`](../R/inspect_paper_outputs.R)
- [`R/extract_variables_from_final_interpretation.R`](../R/extract_variables_from_final_interpretation.R)
- manual pages in [`man/`](../man)

## Table Display Helper

The table display helper can display:

- stored normalized-table JSON such as `normalized_tables.json`
- row-oriented payload JSON such as `llm_input.json`
- parsed-table-style JSON that contains `variables`, `columns`, and `values`
- trace wrapper files that store the actual payload under `payload`, `interpretation`, or `response`

It is intended only for human inspection.

## Command-line usage

```bash
Rscript R/visualize_table_from_json.R parseTable1.out/papers/cobaltpaper/normalized_tables.json
```

## Interactive R usage

From the repo root:

```r
source("R/visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("trace_output/cobaltpaper/table_0/llm_input.json")
visualize_table_from_json("parseTable1.out/papers/cobaltpaper/normalized_tables.json")
```

From inside the `R/` directory:

```r
source("visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("../trace_output/cobaltpaper/table_0/llm_input.json")
```

## Variable Extraction Helper

The variable-extraction helper reads `final_interpretation.json` from one parser output directory and returns a small base-R structure for human inspection of:

- variable names
- original labels
- inferred units
- cleaned level labels
- original level labels
- variable type when available

It uses the current `final_interpretation.json` shape already produced by the parser:

- top-level `interpretation`
- `interpretation$variables`
- `variable_name`
- `variable_type`
- `levels[[i]]$label`

### Interactive usage

From the repo root:

```r
source("R/extract_variables_from_final_interpretation.R")
x <- extract_variables_from_output_dir("trace_output/cobaltpaper/table_0")
print_variable_structure(x)
```

## Paper Output Inspection Helper

The paper-output inspection helper is for comparing deterministic and LLM semantics and reading the supporting paper context.

Public functions:

- `load_paper_outputs(paper_dir)`
- `compare_table_definitions(paper_dir, table_index = 0L)`
- `compare_table_definition_runs(paper_dir_a, paper_dir_b, table_index = 0L, variant_a = "deterministic", variant_b = "llm", label_a = NULL, label_b = NULL)`
- `show_table_context(paper_dir, table_index = 0L, match_type = NULL)`
- `show_llm_evidence(paper_dir, table_index = 0L)`

These helpers use the same per-paper output directory already written by `table1-parser parse`.

### Interactive usage

From the repo root:

```r
source("R/inspect_paper_outputs.R")

x <- load_paper_outputs("parseTable1.out/papers/cobaltpaper")
compare_table_definitions("parseTable1.out/papers/cobaltpaper", table_index = 0L)
compare_table_definition_runs(
  "parse_runs/nephro_no_llm/papers/Nephro",
  "parse_runs/nephro_with_llm/papers/Nephro",
  table_index = 0L,
  variant_a = "deterministic",
  variant_b = "llm",
  label_a = "no_llm",
  label_b = "with_llm_llm"
)
show_table_context("parseTable1.out/papers/cobaltpaper", table_index = 0L, match_type = "table_reference")
show_llm_evidence("parseTable1.out/papers/cobaltpaper", table_index = 0L)
```

What these are for:

- `compare_table_definitions(...)`
  compare deterministic syntax-first semantics with the LLM semantic interpretation
- `compare_table_definition_runs(...)`
  compare any two saved `table_definitions` variants, including cross-run comparisons such as `no_llm` deterministic vs `with_llm` semantic LLM
- `show_table_context(...)`
  inspect the retrieved passages for one table
- `show_llm_evidence(...)`
  resolve `evidence_passage_ids` in the LLM output back to the actual retrieved passages

Current limitation:

- the context helpers currently expose `section_id`, `heading`, `passage_id`, and passage text
- they do not yet expose page-number or line-number anchors

Example output:

```text
Age [units: years]
  original: Age (years), mean (SD)

Sex
  original: Sex, n (%)
  levels:
    Male
    Female
```

### Notes on cleaning

- label cleaning is conservative
- units are preserved when they appear meaningful
- summary suffixes such as `n (%)` and `mean (SD)` are removed from the display name when appropriate
- the original label and original level labels are preserved in the returned structure

## Example Workflow

This is the simplest end-to-end workflow for one PDF:

1. Generate parser trace artifacts:

```bash
python3 scripts/debug_llm_trace.py testpapers/OPEandRA.pdf --use-configured-client
```

This creates a directory such as:

```text
trace_output/OPEandRA/table_0/
```

2. Inspect the table payload visually:

```bash
Rscript R/visualize_table_from_json.R trace_output/OPEandRA/table_0/llm_input.json
```

3. Read the final interpreted variables:

```bash
Rscript -e 'source("R/extract_variables_from_final_interpretation.R"); x <- extract_variables_from_output_dir("trace_output/OPEandRA/table_0"); print_variable_structure(x)'
```

4. Do the same in interactive R if preferred:

```r
source("R/visualize_table_from_json.R")
source("R/extract_variables_from_final_interpretation.R")
options(width = 200)

visualize_table_from_json("trace_output/OPEandRA/table_0/llm_input.json")
x <- extract_variables_from_output_dir("trace_output/OPEandRA/table_0")
print_variable_structure(x)
```

## Notes

- Both helpers use base R only.
- The inspection helpers are documented with small future-compatible `.Rd` files under `man/`.
- It requires the `jsonlite` package.
- Level rows are indented for readability when that structure is present.
- Increasing `options(width = ...)` can make wide tables easier to inspect in the console.
