"""Deterministic per-table retrieval from paper markdown sections."""

from __future__ import annotations

import re

from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import PaperSection, RetrievedPassage, TableContext, TableDefinition
from table1_parser.text_cleaning import clean_text


TABLE_NUMBER_PATTERN = re.compile(r"\bTable\s+(\d+)\b", re.IGNORECASE)
PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")


def build_table_contexts(
    sections: list[PaperSection],
    table_definitions: list[TableDefinition],
) -> list[TableContext]:
    """Build per-table retrieval bundles from parsed sections and table definitions."""
    return [
        build_table_context(table_index, definition, sections)
        for table_index, definition in enumerate(table_definitions)
    ]


def build_table_context(
    table_index: int,
    definition: TableDefinition,
    sections: list[PaperSection],
) -> TableContext:
    """Build one per-table context bundle."""
    table_label = None
    for text in (definition.title, definition.caption):
        match = TABLE_NUMBER_PATTERN.search(text or "")
        if match is not None:
            table_label = f"Table {match.group(1)}"
            break
    row_terms = _dedupe(
        [
            variable.variable_label
            for variable in definition.variables
            if clean_text(variable.variable_label)
        ]
    )
    column_terms = _dedupe(
        [
            column.column_label
            for column in definition.column_definition.columns
            if clean_text(column.column_label) and column.inferred_role not in {"overall", "p_value", "smd"}
        ]
    )
    grouping_terms = _dedupe(
        [
            term
            for term in [
                definition.column_definition.grouping_label or "",
                definition.column_definition.grouping_name or "",
            ]
            if clean_text(term)
        ]
    )
    methods_sections = [section.section_id for section in sections if section.role_hint == "methods_like"]
    results_sections = [section.section_id for section in sections if section.role_hint == "results_like"]
    ranked: list[tuple[float, RetrievedPassage]] = []
    search_terms = row_terms + column_terms + grouping_terms
    normalized_terms = {normalize_label_text(term).lower() for term in search_terms if normalize_label_text(term)}
    for section in sections:
        paragraphs = (
            [chunk for chunk in (clean_text(part) for part in PARAGRAPH_SPLIT_PATTERN.split(section.content)) if chunk]
            if section.content
            else []
        )
        for paragraph_index, paragraph in enumerate(paragraphs):
            lowered = paragraph.lower()
            if table_label and table_label.lower() in lowered:
                ranked.append(
                    (
                        1.0,
                        _passage(
                            section,
                            paragraph_index,
                            paragraph,
                            "table_reference",
                            1.0,
                        ),
                    )
                )
                continue
            if normalized_terms:
                normalized_paragraph = normalize_label_text(paragraph).lower()
                score = sum(term in normalized_paragraph for term in normalized_terms if term) / len(normalized_terms)
            else:
                score = 0.0
            if score <= 0.0:
                continue
            if section.role_hint == "methods_like":
                ranked.append(
                    (
                        score + 0.2,
                        _passage(section, paragraph_index, paragraph, "methods_term_match", round(score + 0.2, 4)),
                    )
                )
            elif section.role_hint == "results_like":
                ranked.append(
                    (
                        score + 0.1,
                        _passage(section, paragraph_index, paragraph, "results_term_match", round(score + 0.1, 4)),
                    )
                )
    passages: list[RetrievedPassage] = []
    seen_passage_text: set[str] = set()
    for passage in [passage for _, passage in sorted(ranked, key=lambda item: -item[0])][:8]:
        if passage.text in seen_passage_text:
            continue
        seen_passage_text.add(passage.text)
        passages.append(passage)
    return TableContext(
        table_id=definition.table_id,
        table_index=table_index,
        table_label=table_label,
        title=definition.title,
        caption=definition.caption,
        row_terms=row_terms,
        column_terms=column_terms,
        grouping_terms=grouping_terms,
        methods_like_section_ids=methods_sections,
        results_like_section_ids=results_sections,
        passages=passages,
    )


def _passage(
    section: PaperSection,
    paragraph_index: int,
    paragraph: str,
    match_type: str,
    score: float,
) -> RetrievedPassage:
    """Build one retrieved passage model."""
    return RetrievedPassage(
        passage_id=f"{section.section_id}_p{paragraph_index}",
        section_id=section.section_id,
        heading=section.heading,
        text=paragraph,
        match_type=match_type,
        score=score,
    )


def _dedupe(values: list[str]) -> list[str]:
    """Deduplicate strings while preserving order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped
