# R Visualization

The repository includes a small base-R helper for visually inspecting one JSON file produced by the parser.

File:

- [`R/visualize_table_from_json.R`](/Users/robert/Projects/Epiconnector/parseTable1/R/visualize_table_from_json.R)

## What it supports

The helper can display:

- row-oriented payload JSON such as `llm_input.json`
- parsed-table-style JSON that contains `variables`, `columns`, and `values`
- trace wrapper files that store the actual payload under `payload`, `interpretation`, or `response`

It is intended only for human inspection.

## Command-line usage

```bash
Rscript R/visualize_table_from_json.R trace_output/cobaltpaper/table_0/llm_input.json
```

## Interactive R usage

From the repo root:

```r
source("R/visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("trace_output/cobaltpaper/table_0/llm_input.json")
```

From inside the `R/` directory:

```r
source("visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("../trace_output/cobaltpaper/table_0/llm_input.json")
```

## Notes

- The helper uses base R only.
- It requires the `jsonlite` package.
- Level rows are indented for readability when that structure is present.
- Increasing `options(width = ...)` can make wide tables easier to inspect in the console.
