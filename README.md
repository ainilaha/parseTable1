# parseTable1

Research-oriented tooling for extracting, normalizing, heuristically interpreting, and LLM-refining Table 1-style epidemiology tables from PDFs.

## Current Components

- PDF extraction into `ExtractedTable`
- normalization into `NormalizedTable`
- deterministic heuristics for row structure, variable blocks, column roles, and value patterns
- parse-quality diagnostics
- Phase 5 LLM refinement with provider-backed OpenAI integration
- debug scripts for pipeline inspection and LLM tracing
- a small R helper for human-readable table visualization from JSON

## Install

```bash
python3 -m pip install -e '.[dev]'
```

## Useful Debug Scripts

Pipeline summary:

```bash
python3 scripts/debug_pipeline.py testpapers/OPEandRA.pdf
```

Diagnostics:

```bash
python3 scripts/debug_quality_report.py testpapers/OPEandRA.pdf
```

Phase 5 LLM trace with a real configured client:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --use-configured-client
```

The trace script writes:

- `heuristics.json`
- `llm_input.json`
- `llm_output.json`
- `final_interpretation.json`
- `diff.txt`

If you do not want to call a live provider, you must pass an explicit canned response:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --response-json path/to/response.json
```

## LLM Configuration

Phase 5 uses environment-variable-based configuration and fails clearly if the provider is not configured.

Minimum OpenAI setup:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4.1-mini
export LLM_TEMPERATURE=0
export LLM_TIMEOUT_SECONDS=60
export LLM_MAX_RETRIES=2
export LLM_DEBUG=false
```

More detail:

- [`docs/llm_integration.md`](docs/llm_integration.md)
- [`docs/llm_setup.md`](docs/llm_setup.md)

## R Visualization

The repository includes small base-R helpers for visual inspection of parser JSON files:

```bash
Rscript R/visualize_table_from_json.R trace_output/cobaltpaper/table_0/llm_input.json
```

and for extracting variable structure from a Phase 5 `final_interpretation.json` directory:

```bash
Rscript -e 'source("R/extract_variables_from_final_interpretation.R"); x <- extract_variables_from_output_dir("trace_output/cobaltpaper/table_0"); print_variable_structure(x)'
```

From an interactive R session:

```r
source("R/visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("trace_output/cobaltpaper/table_0/llm_input.json")

source("R/extract_variables_from_final_interpretation.R")
x <- extract_variables_from_output_dir("trace_output/cobaltpaper/table_0")
print_variable_structure(x)
```

More detail:

- [`docs/r_visualization.md`](docs/r_visualization.md)

## Example Workflow

From the repo root, a typical inspect-and-read workflow looks like this:

1. Run the parser trace on one PDF and write JSON artifacts:

```bash
python3 scripts/debug_llm_trace.py testpapers/OPEandRA.pdf --use-configured-client
```

2. Visually inspect the table-oriented payload that was sent into the Phase 5 layer:

```bash
Rscript R/visualize_table_from_json.R trace_output/OPEandRA/table_0/llm_input.json
```

3. Extract the final interpreted variable structure for human review:

```bash
Rscript -e 'source("R/extract_variables_from_final_interpretation.R"); x <- extract_variables_from_output_dir("trace_output/OPEandRA/table_0"); print_variable_structure(x)'
```

4. If you prefer interactive R:

```r
source("R/visualize_table_from_json.R")
source("R/extract_variables_from_final_interpretation.R")
options(width = 200)

visualize_table_from_json("trace_output/OPEandRA/table_0/llm_input.json")
x <- extract_variables_from_output_dir("trace_output/OPEandRA/table_0")
print_variable_structure(x)
```
