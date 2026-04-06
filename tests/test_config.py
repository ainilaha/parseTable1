"""Configuration tests for the Phase 1 scaffold."""

from __future__ import annotations

from table1_parser.config import Settings


def test_settings_defaults(monkeypatch) -> None:
    """Settings should expose the documented defaults."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_MODEL", raising=False)
    monkeypatch.delenv("QWEN_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    monkeypatch.delenv("LLM_DEBUG", raising=False)
    monkeypatch.delenv("LLM_SDK_DEBUG", raising=False)
    settings = Settings()

    assert settings.default_extraction_backend == "pymupdf4llm"
    assert settings.llm_enabled is False
    assert settings.llm_provider == "openai"
    assert settings.llm_model is None
    assert settings.openai_api_key is None
    assert settings.openai_model is None
    assert settings.qwen_api_key is None
    assert settings.qwen_model is None
    assert settings.qwen_base_url is None
    assert settings.llm_temperature == 0.0
    assert settings.llm_timeout_seconds == 60.0
    assert settings.llm_max_retries == 2
    assert settings.llm_debug is False
    assert settings.llm_sdk_debug is False
    assert settings.max_table_candidates == 10
    assert settings.heuristic_confidence_threshold == 0.7
