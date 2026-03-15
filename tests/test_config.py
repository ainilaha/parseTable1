"""Configuration tests for the Phase 1 scaffold."""

from __future__ import annotations

from table1_parser.config import Settings


def test_settings_defaults() -> None:
    """Settings should expose the documented defaults."""
    settings = Settings()

    assert settings.default_extraction_backend == "pdfplumber"
    assert settings.use_ocr_fallback is False
    assert settings.llm_enabled is False
    assert settings.llm_model is None
    assert settings.max_table_candidates == 10
    assert settings.heuristic_confidence_threshold == 0.7
