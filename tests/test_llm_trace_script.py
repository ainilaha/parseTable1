"""Tests for the Phase 5 trace script behavior."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _script_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "DASHSCOPE_API_KEY",
        "QWEN_MODEL",
        "QWEN_BASE_URL",
        "LLM_TEMPERATURE",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
        "LLM_DEBUG",
    ):
        env.pop(key, None)
    return env


def test_debug_llm_trace_requires_explicit_llm_source() -> None:
    """The trace script should not silently fake an LLM call when no source is configured."""
    result = subprocess.run(
        [sys.executable, "scripts/debug_llm_trace.py", "testpapers/cobaltpaper.pdf"],
        cwd=REPO_ROOT,
        env=_script_env(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "No LLM source configured" in result.stdout
    assert "--use-configured-client" in result.stdout
    assert "--response-json" in result.stdout


def test_debug_llm_trace_reports_missing_provider_configuration() -> None:
    """Configured-client mode should fail clearly when the provider env vars are not set."""
    result = subprocess.run(
        [sys.executable, "scripts/debug_llm_trace.py", "testpapers/cobaltpaper.pdf", "--use-configured-client"],
        cwd=REPO_ROOT,
        env=_script_env(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "LLM configuration error" in result.stdout
    assert "OPENAI_API_KEY" in result.stdout or "OPENAI_MODEL" in result.stdout
    assert "Configure either OpenAI" in result.stdout
    assert "Qwen" in result.stdout
