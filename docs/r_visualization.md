# R Visualization

The repository includes small base-R helpers for visually inspecting parser JSON output.

File:

- [`R/visualize_table_from_json.R`](../R/visualize_table_from_json.R)
- [`R/extract_variables_from_final_interpretation.R`](../R/extract_variables_from_final_interpretation.R)

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
- It requires the `jsonlite` package.
- Level rows are indented for readability when that structure is present.
- Increasing `options(width = ...)` can make wide tables easier to inspect in the console.
