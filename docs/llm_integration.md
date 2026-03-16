# LLM Integration

Phase 5 can call a real LLM provider through the provider abstraction in `table1_parser.llm`.

## Environment variables

Set these before using the configured client:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4.1-mini
export LLM_TEMPERATURE=0
export LLM_TIMEOUT_SECONDS=60
export LLM_MAX_RETRIES=2
export LLM_DEBUG=false
```

Required when `LLM_PROVIDER=openai`:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## Python usage

```python
from table1_parser.extract import build_extractor
from table1_parser.llm import parse_table_with_configured_llm
from table1_parser.normalize import normalize_extracted_table

extractor = build_extractor("pdfplumber")
table = extractor.extract("testpapers/cobaltpaper.pdf")[0]
normalized = normalize_extracted_table(table)
result = parse_table_with_configured_llm(normalized, trace_dir="trace_output/cobaltpaper/table_0")
```

## Debug trace script

The trace script can call the configured provider directly:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --use-configured-client
```

That writes:

- `heuristics.json`
- `llm_input.json`
- `llm_output.json`
- `final_interpretation.json`
- `diff.txt`
