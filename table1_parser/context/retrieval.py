"""Deterministic per-table retrieval from paper markdown sections."""

from __future__ import annotations

import re

from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import DocumentReference, PaperSection, RetrievedPassage, TableContext, TableDefinition
from table1_parser.text_cleaning import clean_text


TABLE_NUMBER_PATTERN = re.compile(r"\bTable\s+(\d+)\b", re.IGNORECASE)
DOCUMENT_REFERENCE_PATTERN = re.compile(r"\b(?P<kind>Table|Tables|Fig\.?|Figs\.?|Figure|Figures)\s+(?P<number>[A-Za-z]?\d+[A-Za-z]?)\b")
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


def build_document_references(sections: list[PaperSection]) -> list[DocumentReference]:
    """Collect table and figure references from markdown-derived paper sections."""
    references: list[DocumentReference] = []
    for section in sections:
        paragraphs = _section_paragraphs(section)
        for paragraph_index, paragraph in enumerate(paragraphs):
            previous_text = paragraphs[paragraph_index - 1] if paragraph_index > 0 else None
            next_text = paragraphs[paragraph_index + 1] if paragraph_index + 1 < len(paragraphs) else None
            for match_index, match in enumerate(DOCUMENT_REFERENCE_PATTERN.finditer(paragraph)):
                reference_kind = "table" if match.group("kind").lower().startswith("table") else "figure"
                reference_label = (
                    f"Table {match.group('number')}"
                    if reference_kind == "table"
                    else f"Figure {match.group('number')}"
                )
                references.append(
                    DocumentReference(
                        reference_id=f"{section.section_id}_p{paragraph_index}_r{match_index}",
                        reference_kind=reference_kind,
                        reference_label=reference_label,
                        reference_number=match.group("number"),
                        section_id=section.section_id,
                        heading=section.heading,
                        role_hint=section.role_hint,
                        paragraph_index=paragraph_index,
                        start_char=match.start(),
                        end_char=match.end(),
                        text=paragraph,
                        previous_text=previous_text,
                        next_text=next_text,
                    )
                )
    return references


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
    document_references = build_document_references(sections)
    table_reference_labels = {table_label.lower()} if table_label else set()
    for section in sections:
        paragraphs = _section_paragraphs(section)
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
                            document_references,
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
                        _passage(
                            section,
                            paragraph_index,
                            paragraph,
                            "methods_term_match",
                            round(score + 0.2, 4),
                            document_references,
                        ),
                    )
                )
            elif section.role_hint == "results_like":
                ranked.append(
                    (
                        score + 0.1,
                        _passage(
                            section,
                            paragraph_index,
                            paragraph,
                            "results_term_match",
                            round(score + 0.1, 4),
                            document_references,
                        ),
                    )
                )
    passages: list[RetrievedPassage] = []
    seen_passage_text: set[str] = set()
    for passage in [passage for _, passage in sorted(ranked, key=lambda item: -item[0])][:8]:
        if passage.text in seen_passage_text:
            continue
        seen_passage_text.add(passage.text)
        passages.append(passage)
        for reference in passage.references:
            if reference.reference_kind == "table" and reference.reference_label.lower() in table_reference_labels:
                table_reference_labels.add(reference.reference_label.lower())
    table_references = [
        reference
        for reference in document_references
        if reference.reference_kind == "table" and reference.reference_label.lower() in table_reference_labels
    ]
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
        references=table_references,
    )


def _passage(
    section: PaperSection,
    paragraph_index: int,
    paragraph: str,
    match_type: str,
    score: float,
    document_references: list[DocumentReference],
) -> RetrievedPassage:
    """Build one retrieved passage model."""
    return RetrievedPassage(
        passage_id=f"{section.section_id}_p{paragraph_index}",
        section_id=section.section_id,
        heading=section.heading,
        text=paragraph,
        match_type=match_type,
        score=score,
        references=[
            reference
            for reference in document_references
            if reference.section_id == section.section_id and reference.paragraph_index == paragraph_index
        ],
    )


def _section_paragraphs(section: PaperSection) -> list[str]:
    """Return cleaned paragraph chunks for one markdown-derived section."""
    return (
        [chunk for chunk in (clean_text(part) for part in PARAGRAPH_SPLIT_PATTERN.split(section.content)) if chunk]
        if section.content
        else []
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
