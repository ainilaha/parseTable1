# parseTable1

Research-oriented tooling for extracting and interpreting Table 1-style epidemiology tables from PDFs.

## LLM Configuration

Phase 5 now supports a real provider-backed LLM client through environment-variable configuration.

Setup overview:

1. Install dependencies:

```bash
python3 -m pip install -e '.[dev]'
```

2. Set provider configuration:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4.1-mini
export LLM_TEMPERATURE=0
export LLM_TIMEOUT_SECONDS=60
export LLM_MAX_RETRIES=2
export LLM_DEBUG=false
```

3. Run the Phase 5 trace script with the configured client:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --use-configured-client
```

More detail is in [`docs/llm_integration.md`](/Users/robert/Projects/Epiconnector/parseTable1/docs/llm_integration.md).
