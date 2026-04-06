"""Markdown section parsing for paper-level context retrieval."""

from __future__ import annotations

import re

from table1_parser.schemas import PaperSection
from table1_parser.text_cleaning import clean_text


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
ABSTRACT_HINTS = ("abstract",)
METHODS_HINTS = (
    "method",
    "materials and methods",
    "patients and methods",
    "study design",
    "study population",
    "measurement",
    "covariate",
    "exposure",
    "statistical analysis",
)
RESULTS_HINTS = ("result", "findings")
DISCUSSION_HINTS = ("discussion",)
CONCLUSION_HINTS = ("conclusion", "conclusions", "summary")
REFERENCES_HINTS = ("reference", "references", "bibliography", "works cited")


def parse_markdown_sections(markdown: str) -> list[PaperSection]:
    """Parse markdown into a linear list of sections with simple role hints."""
    sections: list[PaperSection] = []
    current_heading: str | None = None
    current_level = 0
    current_lines: list[str] = []
    order = 0

    for raw_line in markdown.splitlines():
        match = HEADING_PATTERN.match(raw_line.strip())
        if match is None:
            current_lines.append(raw_line)
            continue
        if current_heading is not None or current_lines:
            sections.append(_build_section(order, current_heading, current_level, current_lines))
            order += 1
        current_heading = clean_text(match.group(2))
        current_level = len(match.group(1))
        current_lines = []

    if current_heading is not None or current_lines:
        sections.append(_build_section(order, current_heading, current_level, current_lines))

    return sections or [PaperSection(section_id="section_0", order=0, content=clean_text(markdown))]


def paper_sections_to_payload(sections: list[PaperSection]) -> list[dict[str, object]]:
    """Serialize paper sections as JSON-friendly dictionaries."""
    return [section.model_dump(mode="json") for section in sections]


def _build_section(order: int, heading: str | None, level: int, lines: list[str]) -> PaperSection:
    """Build one section object from heading and collected lines."""
    content = clean_text("\n".join(lines))
    lowered = clean_text(heading or "").lower()
    return PaperSection(
        section_id=f"section_{order}",
        order=order,
        heading=heading,
        level=level,
        role_hint=(
            "abstract_like"
            if any(token in lowered for token in ABSTRACT_HINTS)
            else (
                "methods_like"
                if any(token in lowered for token in METHODS_HINTS)
                else (
                    "results_like"
                    if any(token in lowered for token in RESULTS_HINTS)
                    else (
                        "discussion_like"
                        if any(token in lowered for token in DISCUSSION_HINTS)
                        else (
                            "conclusion_like"
                            if any(token in lowered for token in CONCLUSION_HINTS)
                            else ("references_like" if any(token in lowered for token in REFERENCES_HINTS) else "other")
                        )
                    )
                )
            )
        ),
        content=content,
    )
