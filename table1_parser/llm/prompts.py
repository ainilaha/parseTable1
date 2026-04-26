"""Shared prompt-template helpers for LLM modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from table1_parser.text_cleaning import clean_text


@lru_cache(maxsize=None)
def load_prompt_template(path: str | Path) -> str:
    """Load a prompt template from disk with simple in-process caching."""
    return Path(path).read_text(encoding="utf-8")


def render_prompt_template(template: str, substitutions: dict[str, str]) -> str:
    """Render a prompt template with simple placeholder substitution."""
    rendered = template
    for key, value in substitutions.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def merge_prompt_table_text(title: str | None, caption: str | None) -> str | None:
    """Merge table title and caption into one compact prompt-facing description."""
    cleaned_title = clean_text(title or "")
    cleaned_caption = clean_text(caption or "")
    if cleaned_title and cleaned_caption:
        lowered_title = cleaned_title.lower()
        lowered_caption = cleaned_caption.lower()
        if lowered_title.startswith("table ") and not lowered_caption.startswith("table "):
            return cleaned_caption
        if lowered_title in lowered_caption:
            return cleaned_caption
        if lowered_caption in lowered_title:
            return cleaned_title
        return f"{cleaned_title} | {cleaned_caption}"
    if cleaned_title:
        return cleaned_title
    if cleaned_caption:
        return cleaned_caption
    return None
