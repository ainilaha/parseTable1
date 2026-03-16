"""Tests for provider-backed LLM client wiring."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from table1_parser.config import Settings
from table1_parser.llm.client import LLMConfigurationError, LLMProviderError, build_llm_client
from table1_parser.llm.schemas import LLMTableInterpretation


class _FakeResponsesAPI:
    def __init__(self, response: object) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self._response


class _FakeOpenAI:
    def __init__(self, *, api_key: str, timeout: float, max_retries: int) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.responses = _FakeResponsesAPI(
            SimpleNamespace(
                output_parsed=LLMTableInterpretation(
                    table_id="tbl-llm",
                    variables=[],
                    columns=[],
                    notes=["from fake openai"],
                )
            )
        )


def test_settings_reads_llm_environment_variables(monkeypatch) -> None:
    """Settings should read the documented LLM environment variables directly."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.1")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_DEBUG", "true")

    settings = Settings()

    assert settings.llm_provider == "openai"
    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "gpt-4.1-mini"
    assert settings.llm_model == "gpt-4.1-mini"
    assert settings.llm_temperature == 0.1
    assert settings.llm_timeout_seconds == 30
    assert settings.llm_max_retries == 4
    assert settings.llm_debug is True


def test_build_llm_client_requires_openai_configuration(monkeypatch) -> None:
    """Missing required OpenAI settings should fail with a clear configuration error."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    settings = Settings(llm_provider="openai", openai_model="gpt-4.1-mini")

    with pytest.raises(LLMConfigurationError) as exc_info:
        build_llm_client(settings=settings)

    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_build_llm_client_returns_openai_client_with_fake_sdk(monkeypatch) -> None:
    """The provider builder should construct an OpenAI-backed client from configured settings."""
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    settings = Settings(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4.1-mini",
        llm_temperature=0.2,
        llm_timeout_seconds=15,
        llm_max_retries=3,
    )

    client = build_llm_client(settings=settings)
    response = client.structured_completion(
        "prompt text",
        LLMTableInterpretation.model_json_schema(),
        response_model=LLMTableInterpretation,
    )

    assert response["table_id"] == "tbl-llm"
    assert response["notes"] == ["from fake openai"]
    assert client._client.api_key == "test-key"  # type: ignore[attr-defined]
    assert client._client.timeout == 15  # type: ignore[attr-defined]
    assert client._client.max_retries == 3  # type: ignore[attr-defined]
    assert client._client.responses.calls[0]["model"] == "gpt-4.1-mini"  # type: ignore[attr-defined]


def test_openai_client_raises_provider_error_when_no_parsed_payload(monkeypatch) -> None:
    """A provider response without structured parsed content should fail clearly."""
    broken_openai = SimpleNamespace(
        OpenAI=lambda **kwargs: SimpleNamespace(
            responses=_FakeResponsesAPI(SimpleNamespace(output_parsed=None, output_text="not json"))
        )
    )
    monkeypatch.setitem(sys.modules, "openai", broken_openai)
    client = build_llm_client(
        settings=Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            openai_model="gpt-4.1-mini",
        )
    )

    with pytest.raises(LLMProviderError):
        client.structured_completion(
            "prompt text",
            LLMTableInterpretation.model_json_schema(),
            response_model=LLMTableInterpretation,
        )
