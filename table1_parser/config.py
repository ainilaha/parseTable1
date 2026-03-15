"""Application configuration for the Table 1 parser."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:
    class SettingsConfigDict(dict):
        """Fallback settings config when pydantic-settings is unavailable."""

    class BaseSettings(BaseModel):
        """Minimal BaseSettings-compatible fallback for local development."""

        model_config = ConfigDict(extra="ignore")

        def __init__(self, **data: object) -> None:
            merged_data = self._load_environment_defaults()
            merged_data.update(data)
            super().__init__(**merged_data)

        @classmethod
        def _load_environment_defaults(cls) -> dict[str, object]:
            prefix = ""
            config = getattr(cls, "model_config", None)
            if isinstance(config, dict):
                prefix = str(config.get("env_prefix", ""))

            values: dict[str, object] = {}
            for field_name in cls.model_fields:
                env_name = f"{prefix}{field_name}".upper()
                if env_name in os.environ:
                    values[field_name] = os.environ[env_name]
            return values


class Settings(BaseSettings):
    """Runtime configuration for the Table 1 parser."""

    default_extraction_backend: str = Field(default="pdfplumber")
    use_ocr_fallback: bool = Field(default=False)
    llm_enabled: bool = Field(default=False)
    llm_model: str | None = Field(default=None)
    max_table_candidates: int = Field(default=10, ge=1)
    heuristic_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_prefix="TABLE1_PARSER_",
        extra="ignore",
    )
