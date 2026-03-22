# parseTable1

Research-oriented tooling for extracting, normalizing, heuristically interpreting, and LLM-refining Table 1-style epidemiology tables from PDFs.

## Current Status

- The main user command is now `table1-parser parse`, which runs the available pipeline stages once and writes all currently available paper outputs.
- The `extract` and `normalize` commands are still available for stage-specific inspection and debugging.
- `TableDefinition` is now implemented as a deterministic, value-free semantic representation of the table structure.
- The final semantic `ParsedTable` stage is not implemented yet.
- The repository also contains heuristic interpretation, diagnostics, and LLM-oriented developer tooling.

## Basic Idea

The goal of this project is to parse Table 1-style tables from epidemiology papers into structured representations that can be inspected, validated, and used by downstream tools.

The intended pipeline is:

```text
PDF -> ExtractedTable -> NormalizedTable -> TableDefinition -> ParsedTable
```

Each stage has a different purpose:

- `ExtractedTable`
  Raw table extraction from the PDF. This preserves the recovered grid, cell text, page information, and extraction metadata.

- `NormalizedTable`
  A cleaned and organized version of the extracted table. This separates header rows from body rows, preserves row structure, and computes row-level signals that help later interpretation.

- `TableDefinition`
  The value-free semantic stage. This captures which variables appear in the rows, which ones are categorical, what their levels are, and how the columns were constructed, without including the table's printed values.

- `ParsedTable`
  The final semantic output. This combines variable definitions, column meanings, and parsed table values into a structured format.

This separation is intentional. It keeps extraction, normalization, semantic interpretation, and final value output distinct, which makes the system easier to debug and safer to extend.

At the moment, the repository can persist:

- `ExtractedTable`
- `NormalizedTable`
- `TableDefinition`
- paper-level markdown context

Today, a single call to `table1-parser parse` writes those artifacts from one extraction pass.

## Install

Clone the repository and enter the project directory:

```bash
git clone <repo-url>
cd parseTable1
```

```bash
python3 -m pip install -e .
```

## Quick Start

Run the available parse pipeline once and write all current stage outputs:

```bash
table1-parser parse path/to/paper.pdf
```

By default this writes:

```text
parseTable1.out/papers/<paper_stem>/extracted_tables.json
parseTable1.out/papers/<paper_stem>/normalized_tables.json
parseTable1.out/papers/<paper_stem>/table_definitions.json
parseTable1.out/papers/<paper_stem>/paper_markdown.md
parseTable1.out/papers/<paper_stem>/paper_sections.json
parseTable1.out/papers/<paper_stem>/table_contexts/table_0_context.json
```

For example:

```bash
table1-parser parse testpapers/cobaltpaper.pdf
```

This currently writes the extraction, normalization, table-definition, and paper-context outputs in one run. As later stages are implemented, `parse` is intended to write those too.

If you want just the raw extraction stage:

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

If you want just the normalization stage:

```bash
table1-parser normalize path/to/paper.pdf
```

By default this writes JSON to:

```bash
parseTable1.out/papers/<paper_stem>/normalized_tables.json
```

## R Visualization

The repository includes small base-R helpers for visual inspection of normalized, parsed, and trace-oriented JSON files.

```bash
Rscript R/visualize_table_from_json.R parseTable1.out/papers/cobaltpaper/normalized_tables.json
```

From an interactive R session:

```r
source("R/visualize_table_from_json.R")
options(width = 200)
visualize_table_from_json("parseTable1.out/papers/cobaltpaper/normalized_tables.json")
```

More detail:

- [`docs/parsing_process.md`](docs/parsing_process.md)
- [`docs/r_visualization.md`](docs/r_visualization.md)
- [`docs/parsing_output_design.md`](docs/parsing_output_design.md)

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
      normalized_tables.json
      table_definitions.json
      paper_markdown.md
      paper_sections.json
      table_contexts/
        table_0_context.json
```

This keeps outputs for each paper in a separate directory and leaves room for later semantic-definition, parsed, and interpretation-stage outputs.
The `parse` command is intended to populate this directory with every available stage output from a single pipeline run.

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

These trace artifacts live under `trace_output/` and are separate from the paper-oriented artifacts under `parseTable1.out/`.

## JSON Contracts

The repository keeps the table pipeline JSON-first. The current output and intermediate JSON design is documented in:

- [`docs/parsing_output_design.md`](docs/parsing_output_design.md)

For the Phase 5 LLM input payload specifically:

- the canonical Pydantic model is `table1_parser.llm.schemas.LLMInputPayload`
- the checked-in JSON schema is [`schemas/table_llm_payload.schema.json`](schemas/table_llm_payload.schema.json)
- the checked-in sample payload is [`tests/data/sample_table_llm_payload.json`](tests/data/sample_table_llm_payload.json)

The test suite includes drift checks to ensure the checked-in schema and sample payload stay aligned with the live `LLMInputPayload` model.
