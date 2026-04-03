"""Provider-agnostic LLM client abstractions."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from table1_parser.config import Settings


class LLMConfigurationError(RuntimeError):
    """Raised when provider-backed LLM configuration is missing or invalid."""


class LLMProviderError(RuntimeError):
    """Raised when the configured LLM provider call fails."""


class LLMClient(ABC):
    """Abstract client for schema-constrained structured completions."""

    @abstractmethod
    def structured_completion(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        response_model: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        """Return a structured JSON-like response that matches the requested schema."""


class StaticStructuredLLMClient(LLMClient):
    """Small test double that returns a preconfigured structured response."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = deepcopy(response)
        self.calls: list[dict[str, Any]] = []

    def structured_completion(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        response_model: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        """Record the call and return the configured response."""
        self.calls.append({"prompt": prompt, "schema": schema, "response_model": response_model})
        return deepcopy(self._response)


class OpenAIClient(LLMClient):
    """OpenAI-backed structured-output client using environment-based configuration."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        sdk_debug: bool = False,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.sdk_debug = sdk_debug
        if self.sdk_debug:
            os.environ.setdefault("OPENAI_LOG", "debug")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise LLMConfigurationError(
                "OpenAI SDK is not installed. Install the 'openai' package to enable LLM integration."
            ) from exc

        self._client = OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def structured_completion(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        response_model: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        """Request a structured completion and return a JSON-like dict."""
        if response_model is None:
            raise LLMConfigurationError("OpenAIClient requires a Pydantic response_model for structured parsing.")
        try:
            response = self._client.responses.parse(
                model=self.model,
                input=prompt,
                temperature=self.temperature,
                text_format=response_model,
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI structured completion failed: {exc}") from exc

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            for output_item in getattr(response, "output", []) or []:
                for content_item in getattr(output_item, "content", []) or []:
                    parsed = getattr(content_item, "parsed", None)
                    if parsed is not None:
                        break
                if parsed is not None:
                    break
        if parsed is None:
            output_text = getattr(response, "output_text", None)
            if isinstance(output_text, str) and output_text.strip():
                try:
                    loaded = json.loads(output_text)
                except json.JSONDecodeError:
                    loaded = None
                if isinstance(loaded, dict):
                    parsed = loaded
        if parsed is None:
            raise LLMProviderError("OpenAI response did not contain a parsed structured payload.")
        if isinstance(parsed, BaseModel):
            return parsed.model_dump(mode="json")
        if isinstance(parsed, dict):
            return parsed
        raise LLMProviderError("OpenAI parsed structured payload had an unsupported type.")


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    """Create a configured provider-backed LLM client from environment-driven settings."""
    settings = settings or Settings()
    provider = settings.llm_provider.lower().strip()
    if provider != "openai":
        raise LLMConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")

    api_key = settings.openai_api_key
    model = settings.openai_model or settings.llm_model
    if not api_key:
        raise LLMConfigurationError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
    if not model:
        raise LLMConfigurationError("OPENAI_MODEL is required when LLM_PROVIDER=openai.")

    return OpenAIClient(
        api_key=api_key,
        model=model,
        temperature=settings.llm_temperature,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        sdk_debug=settings.llm_sdk_debug,
    )
