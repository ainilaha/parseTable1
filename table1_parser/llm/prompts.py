"""Shared prompt-template helpers for LLM modules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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
