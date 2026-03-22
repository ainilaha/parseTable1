"""Deterministic per-table retrieval from paper markdown sections."""

from __future__ import annotations

import re

from table1_parser.normalize.cleaner import clean_text
from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import PaperSection, RetrievedPassage, TableContext, TableDefinition


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


def table_contexts_to_payload(contexts: list[TableContext]) -> list[dict[str, object]]:
    """Serialize table contexts as JSON-friendly dictionaries."""
    return [context.model_dump(mode="json") for context in contexts]


def build_table_context(
    table_index: int,
    definition: TableDefinition,
    sections: list[PaperSection],
) -> TableContext:
    """Build one per-table context bundle."""
    table_label = _table_label(definition.title, definition.caption)
    row_terms = _row_terms(definition)
    column_terms = _column_terms(definition)
    grouping_terms = _grouping_terms(definition)
    methods_sections = [section.section_id for section in sections if section.role_hint == "methods_like"]
    results_sections = [section.section_id for section in sections if section.role_hint == "results_like"]
    passages = _retrieve_passages(sections, table_label, row_terms, column_terms, grouping_terms)
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


def _table_label(title: str | None, caption: str | None) -> str | None:
    """Return a normalized table label such as 'Table 2' when present."""
    for text in (title, caption):
        match = TABLE_NUMBER_PATTERN.search(text or "")
        if match is not None:
            return f"Table {match.group(1)}"
    return None


def _row_terms(definition: TableDefinition) -> list[str]:
    """Return row-label terms worth searching in the paper text."""
    return _dedupe(
        [
            variable.variable_label
            for variable in definition.variables
            if clean_text(variable.variable_label)
        ]
    )


def _column_terms(definition: TableDefinition) -> list[str]:
    """Return column-label terms worth searching in the paper text."""
    return _dedupe(
        [
            column.column_label
            for column in definition.column_definition.columns
            if clean_text(column.column_label) and column.inferred_role not in {"overall", "p_value", "smd"}
        ]
    )


def _grouping_terms(definition: TableDefinition) -> list[str]:
    """Return grouping terms worth searching in the paper text."""
    terms = [
        definition.column_definition.grouping_label or "",
        definition.column_definition.grouping_name or "",
    ]
    return _dedupe([term for term in terms if clean_text(term)])


def _retrieve_passages(
    sections: list[PaperSection],
    table_label: str | None,
    row_terms: list[str],
    column_terms: list[str],
    grouping_terms: list[str],
) -> list[RetrievedPassage]:
    """Return a compact retrieved passage list for one table."""
    ranked: list[tuple[float, RetrievedPassage]] = []
    search_terms = row_terms + column_terms + grouping_terms
    normalized_terms = {normalize_label_text(term).lower() for term in search_terms if normalize_label_text(term)}
    for section in sections:
        for paragraph_index, paragraph in enumerate(_paragraphs(section.content)):
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
            score = _term_match_score(paragraph, normalized_terms)
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
    return _dedupe_passages([passage for _, passage in sorted(ranked, key=lambda item: -item[0])][:8])


def _paragraphs(content: str) -> list[str]:
    """Split section content into compact paragraphs."""
    if not content:
        return []
    chunks = [clean_text(part) for part in PARAGRAPH_SPLIT_PATTERN.split(content)]
    return [chunk for chunk in chunks if chunk]


def _term_match_score(paragraph: str, normalized_terms: set[str]) -> float:
    """Return a simple normalized term-overlap score for a paragraph."""
    if not normalized_terms:
        return 0.0
    normalized_paragraph = normalize_label_text(paragraph).lower()
    matches = sum(term in normalized_paragraph for term in normalized_terms if term)
    if matches == 0:
        return 0.0
    return matches / len(normalized_terms)


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


def _dedupe_passages(passages: list[RetrievedPassage]) -> list[RetrievedPassage]:
    """Deduplicate passages by text while preserving rank order."""
    seen: set[str] = set()
    deduped: list[RetrievedPassage] = []
    for passage in passages:
        if passage.text in seen:
            continue
        seen.add(passage.text)
        deduped.append(passage)
    return deduped
