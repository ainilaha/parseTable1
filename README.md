# parseTable1

Research-oriented tooling for extracting, normalizing, heuristically interpreting, and LLM-refining Table 1-style epidemiology tables from PDFs.

## Current Status

- The extraction workflow is available now through the `table1-parser` CLI.
- The full `parse` command is not implemented yet.
- The repository also contains normalization, heuristic interpretation, diagnostics, and LLM-oriented developer tooling.

## Install

```bash
python3 -m pip install -e '.[dev]'
```

## Quick Start

Extract tables from a PDF:

```bash
table1-parser extract path/to/paper.pdf
```

By default this writes JSON to:

```bash
parseTable1.out/papers/<paper_stem>/extracted_tables.json
```

For example:

```bash
table1-parser extract testpapers/cobaltpaper.pdf
```

produces:

```text
parseTable1.out/papers/cobaltpaper/extracted_tables.json
```

If you want the JSON on stdout instead of a file:

```bash
table1-parser extract path/to/paper.pdf --stdout
```

If you want a different root output directory:

```bash
table1-parser extract path/to/paper.pdf --outdir results
```

This writes to:

```text
results/papers/<paper_stem>/extracted_tables.json
```

## R Visualization

The repository includes small base-R helpers for visual inspection of output JSON files.

```bash
Rscript R/visualize_table_from_json.R parseTable1.out/papers/cobaltpaper/extracted_tables.json
```

From an interactive R session:

```r
source("R/visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("parseTable1.out/papers/cobaltpaper/extracted_tables.json")
```

More detail:

- [`docs/r_visualization.md`](docs/r_visualization.md)

## Output Layout

The default root output directory is:

```text
parseTable1.out
```

Under that, outputs are organized by paper:

```text
parseTable1.out/
  papers/
    cobaltpaper/
      extracted_tables.json
```

This keeps outputs for each paper in a separate directory and leaves room for later normalized, parsed, and interpretation-stage outputs.

## LLM Configuration

Phase 5 developer tooling uses environment-variable-based configuration and fails clearly if the provider is not configured.

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

## Developer Tools

The repository also includes internal scripts for pipeline inspection, diagnostics, synthetic data generation, and LLM tracing.

Pipeline summary:

```bash
python3 scripts/debug_pipeline.py testpapers/cobaltpaper.pdf
```

Diagnostics:

```bash
python3 scripts/debug_quality_report.py testpapers/cobaltpaper.pdf
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
