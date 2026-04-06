# LLM Setup

This project supports a real Phase 5 LLM client through environment-variable-based configuration.

## Required variables

When `LLM_PROVIDER=openai`, these must be set:

- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

When `LLM_PROVIDER=qwen`, these must be set:

- `LLM_PROVIDER`
- `DASHSCOPE_API_KEY`
- `QWEN_MODEL`

Optional:

- `LLM_TEMPERATURE`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `LLM_DEBUG`
- `LLM_SDK_DEBUG`
- `QWEN_BASE_URL`

## Example setup on macOS/Linux

OpenAI:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4.1-mini
export LLM_TEMPERATURE=0
export LLM_TIMEOUT_SECONDS=60
export LLM_MAX_RETRIES=2
export LLM_DEBUG=false
export LLM_SDK_DEBUG=false
```

Qwen:

```bash
export LLM_PROVIDER=qwen
export DASHSCOPE_API_KEY=your_api_key_here
export QWEN_MODEL=qwen-plus
export QWEN_BASE_URL=https://dashscope.aliyuncs.com/api/v1
export LLM_TEMPERATURE=0
export LLM_TIMEOUT_SECONDS=60
export LLM_MAX_RETRIES=2
export LLM_DEBUG=false
```

## Example setup on Windows PowerShell

OpenAI:

```powershell
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "your_api_key_here"
$env:OPENAI_MODEL = "gpt-4.1-mini"
$env:LLM_TEMPERATURE = "0"
$env:LLM_TIMEOUT_SECONDS = "60"
$env:LLM_MAX_RETRIES = "2"
$env:LLM_DEBUG = "false"
$env:LLM_SDK_DEBUG = "false"
```

Qwen:

```powershell
$env:LLM_PROVIDER = "qwen"
$env:DASHSCOPE_API_KEY = "your_api_key_here"
$env:QWEN_MODEL = "qwen-plus"
$env:QWEN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
$env:LLM_TEMPERATURE = "0"
$env:LLM_TIMEOUT_SECONDS = "60"
$env:LLM_MAX_RETRIES = "2"
$env:LLM_DEBUG = "false"
```

Meaning of the two debug flags:

- `LLM_DEBUG=true`
  write timestamped semantic-debug JSON artifacts to disk during `parse`
- `LLM_SDK_DEBUG=true`
  enable verbose provider/SDK logging in the terminal

## Install requirement

The configured OpenAI client requires the OpenAI Python SDK:

```bash
python3 -m pip install -e '.[dev]'
```

The configured Qwen client uses the Python standard library HTTP stack.

If provider setup is missing, the trace script and configured client path will fail with a clear setup error.

## Running the configured Phase 5 trace

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --use-configured-client
```

## Explicit offline testing

If you do not want to call a live provider, pass an explicit canned response instead of using the configured client:

```bash
python3 scripts/debug_llm_trace.py testpapers/cobaltpaper.pdf --response-json path/to/response.json
```

## Security

- Do not hardcode API keys in source files.
- Do not commit API keys to the repository.
- Prefer setting credentials in the shell environment or a local untracked secrets file loaded by your shell.
