# LLM Integration

Phase 5 refines the deterministic heuristic interpretation through the provider abstraction in `table1_parser.llm`.

## Current provider path

The repository currently supports:

- `LLM_PROVIDER=openai`

The configured client uses:

- environment variables for credentials and model selection
- the official OpenAI Python SDK
- structured output parsed into the existing Phase 5 Pydantic models

## Environment variables

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4.1-mini
export LLM_TEMPERATURE=0
export LLM_TIMEOUT_SECONDS=60
export LLM_MAX_RETRIES=2
export LLM_DEBUG=false
```

Required for OpenAI:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## Python usage

```python
from table1_parser.extract import build_extractor
from table1_parser.llm import parse_table_with_configured_llm
from table1_parser.normalize import normalize_extracted_table

extractor = build_extractor("pymupdf4llm")
table = extractor.extract("testpapers/cobaltpaper.pdf")[0]
normalized = normalize_extracted_table(table)
result = parse_table_with_configured_llm(
    normalized,
    trace_dir="trace_output/cobaltpaper/table_0",
)
```

## Trace script

Live provider call:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --use-configured-client
```

Explicit canned response:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --response-json path/to/response.json
```

If neither a configured client nor `--response-json` is provided, the script now fails loudly instead of silently faking an LLM run.

## Trace artifacts

The Phase 5 trace path writes:

- `heuristics.json`
- `llm_input.json`
- `llm_output.json`
- `final_interpretation.json`
- `diff.txt`

These are intended for inspection and should not be committed. `trace_output/` is ignored by Git.
