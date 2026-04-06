"""Paper-level candidate variable inventory building."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from table1_parser.normalize.text_normalizer import normalize_label_text
from table1_parser.schemas import (
    PaperSection,
    PaperVariableInventory,
    TableDefinition,
    VariableCandidate,
    VariableMention,
)
from table1_parser.text_cleaning import clean_text


TABLE_NUMBER_PATTERN = re.compile(r"\bTable\s+(\d+)\b", re.IGNORECASE)
PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")

_SECTION_PRIORITY = {
    "abstract_like": 1.0,
    "methods_like": 0.95,
    "conclusion_like": 0.9,
    "discussion_like": 0.85,
    "results_like": 0.65,
    "other": 0.35,
    "references_like": 0.0,
}
_SOURCE_PRIORITY = {
    "text_based": 5,
    "table_variable_name": 4,
    "table_variable_label": 3,
    "table_caption": 2,
    "table_title": 2,
    "table_grouping_label": 1,
}


@dataclass(frozen=True, slots=True)
class _SeedTerm:
    """Internal search term used to build mentions and candidates."""

    candidate_key: str
    raw_label: str
    normalized_label: str
    table_id: str
    table_index: int
    table_label: str | None


def build_paper_variable_inventory(
    paper_id: str,
    sections: list[PaperSection],
    table_definitions: list[TableDefinition],
) -> PaperVariableInventory:
    """Build a conservative paper-level inventory from sections and table definitions."""
    mention_counter = 0
    mentions: list[VariableMention] = []
    seeds: list[_SeedTerm] = []
    seen_mentions: set[tuple[object, ...]] = set()

    for table_index, definition in enumerate(table_definitions):
        table_label = None
        table_seeds: list[_SeedTerm] = []
        for text in (definition.title, definition.caption):
            match = TABLE_NUMBER_PATTERN.search(text or "")
            if match is not None:
                table_label = f"Table {match.group(1)}"
                break

        for variable in definition.variables:
            variable_label = clean_text(variable.variable_label)
            variable_name = clean_text(variable.variable_name)
            candidate_key = _candidate_key(variable_name or variable_label)
            if not candidate_key:
                continue

            if variable_label:
                mention_counter = _append_mention(
                    mentions=mentions,
                    seen_mentions=seen_mentions,
                    mention_counter=mention_counter,
                    raw_label=variable_label,
                    normalized_label=_normalized_label(variable_label),
                    source_type="table_variable_label",
                    table_id=definition.table_id,
                    table_index=table_index,
                    table_label=table_label,
                    priority_weight=0.8,
                    confidence=variable.confidence if variable.confidence is not None else 0.8,
                )
                seeds.append(
                    _SeedTerm(
                        candidate_key=candidate_key,
                        raw_label=variable_label,
                        normalized_label=_normalized_label(variable_label),
                        table_id=definition.table_id,
                        table_index=table_index,
                        table_label=table_label,
                    )
                )
                table_seeds.append(seeds[-1])
            if variable_name and _candidate_key(variable_name) != _candidate_key(variable_label):
                mention_counter = _append_mention(
                    mentions=mentions,
                    seen_mentions=seen_mentions,
                    mention_counter=mention_counter,
                    raw_label=variable_name,
                    normalized_label=_normalized_label(variable_name),
                    source_type="table_variable_name",
                    table_id=definition.table_id,
                    table_index=table_index,
                    table_label=table_label,
                    priority_weight=0.85,
                    confidence=variable.confidence if variable.confidence is not None else 0.82,
                )
                seeds.append(
                    _SeedTerm(
                        candidate_key=candidate_key,
                        raw_label=variable_name,
                        normalized_label=_normalized_label(variable_name),
                        table_id=definition.table_id,
                        table_index=table_index,
                        table_label=table_label,
                    )
                )
                table_seeds.append(seeds[-1])

        for grouping_term in (
            clean_text(definition.column_definition.grouping_name or ""),
            clean_text(definition.column_definition.grouping_label or ""),
        ):
            if not grouping_term:
                continue
            mention_counter = _append_mention(
                mentions=mentions,
                seen_mentions=seen_mentions,
                mention_counter=mention_counter,
                raw_label=grouping_term,
                normalized_label=_normalized_label(grouping_term),
                source_type="table_grouping_label",
                table_id=definition.table_id,
                table_index=table_index,
                table_label=table_label,
                priority_weight=0.7,
                confidence=definition.column_definition.confidence if definition.column_definition.confidence is not None else 0.72,
            )
            seeds.append(
                _SeedTerm(
                    candidate_key=_candidate_key(grouping_term),
                    raw_label=grouping_term,
                    normalized_label=_normalized_label(grouping_term),
                    table_id=definition.table_id,
                    table_index=table_index,
                    table_label=table_label,
                )
            )
            table_seeds.append(seeds[-1])

        for source_text, source_type in (
            (clean_text(definition.title or ""), "table_title"),
            (clean_text(definition.caption or ""), "table_caption"),
        ):
            if not source_text:
                continue
            normalized_source_text = _normalized_label(source_text).lower()
            for seed in table_seeds:
                if not seed.normalized_label or not _term_in_normalized_text(seed.normalized_label.lower(), normalized_source_text):
                    continue
                mention_counter = _append_mention(
                    mentions=mentions,
                    seen_mentions=seen_mentions,
                    mention_counter=mention_counter,
                    raw_label=seed.raw_label,
                    normalized_label=seed.normalized_label,
                    source_type=source_type,
                    evidence_text=source_text,
                    table_id=definition.table_id,
                    table_index=table_index,
                    table_label=table_label,
                    priority_weight=0.72 if source_type == "table_caption" else 0.68,
                    confidence=0.76 if source_type == "table_caption" else 0.72,
                )

    unique_seeds: dict[tuple[str, str], _SeedTerm] = {}
    for seed in seeds:
        if seed.candidate_key and seed.normalized_label:
            unique_seeds.setdefault((seed.candidate_key, seed.normalized_label.lower()), seed)

    for section in sections:
        if section.role_hint == "references_like":
            continue
        paragraphs = (
            [chunk for chunk in (clean_text(part) for part in PARAGRAPH_SPLIT_PATTERN.split(section.content)) if chunk]
            if section.content
            else []
        )
        for paragraph_index, paragraph in enumerate(paragraphs):
            normalized_paragraph = _normalized_label(paragraph).lower()
            for seed in unique_seeds.values():
                if not seed.normalized_label or not _term_in_normalized_text(seed.normalized_label.lower(), normalized_paragraph):
                    continue
                mention_counter = _append_mention(
                    mentions=mentions,
                    seen_mentions=seen_mentions,
                    mention_counter=mention_counter,
                    raw_label=seed.raw_label,
                    normalized_label=seed.normalized_label,
                    source_type="text_based",
                    section_id=section.section_id,
                    heading=section.heading,
                    role_hint=section.role_hint,
                    paragraph_index=paragraph_index,
                    evidence_text=paragraph,
                    priority_weight=_SECTION_PRIORITY.get(section.role_hint, 0.0),
                    confidence=round(min(0.98, 0.45 + 0.5 * _SECTION_PRIORITY.get(section.role_hint, 0.0)), 4),
                )

    candidate_mentions: dict[str, list[VariableMention]] = defaultdict(list)
    for mention in mentions:
        key = _candidate_key(mention.raw_label)
        if key:
            candidate_mentions[key].append(mention)

    candidates: list[VariableCandidate] = []
    for candidate_index, candidate_key in enumerate(sorted(candidate_mentions.keys())):
        grouped_mentions = candidate_mentions[candidate_key]
        preferred = max(
            grouped_mentions,
            key=lambda item: (
                _SOURCE_PRIORITY.get(item.source_type, 0),
                item.priority_weight,
                item.confidence if item.confidence is not None else 0.0,
                -len(item.raw_label),
            ),
        )
        alternate_labels = _unique_preserving_order(
            mention.raw_label for mention in grouped_mentions if mention.raw_label != preferred.raw_label
        )
        text_support_count = sum(mention.source_type == "text_based" for mention in grouped_mentions)
        table_support_count = sum(mention.source_type != "text_based" for mention in grouped_mentions)
        caption_support_count = sum(mention.source_type in {"table_caption", "table_title"} for mention in grouped_mentions)
        priority_score = round(
            min(1.0, max((mention.priority_weight for mention in grouped_mentions), default=0.0) + 0.04 * max(0, len(grouped_mentions) - 1)),
            4,
        )
        confidence = round(
            min(
                0.99,
                0.4
                + 0.08 * text_support_count
                + 0.06 * table_support_count
                + 0.12 * max((mention.priority_weight for mention in grouped_mentions), default=0.0),
            ),
            4,
        )
        candidates.append(
            VariableCandidate(
                candidate_id=f"candidate_{candidate_index}",
                preferred_label=preferred.raw_label,
                normalized_label=candidate_key,
                alternate_labels=alternate_labels,
                supporting_mention_ids=[mention.mention_id for mention in grouped_mentions],
                source_types=_unique_preserving_order(mention.source_type for mention in grouped_mentions),
                section_ids=_unique_preserving_order(mention.section_id for mention in grouped_mentions if mention.section_id),
                section_role_hints=_unique_preserving_order(mention.role_hint for mention in grouped_mentions if mention.role_hint),
                table_ids=_unique_preserving_order(mention.table_id for mention in grouped_mentions if mention.table_id),
                table_indices=_unique_preserving_order(mention.table_index for mention in grouped_mentions if mention.table_index is not None),
                text_support_count=text_support_count,
                table_support_count=table_support_count,
                caption_support_count=caption_support_count,
                priority_score=priority_score,
                confidence=confidence,
                interpretation_status="merged_conservatively" if len(grouped_mentions) > 1 else "uninterpreted",
                notes=[],
            )
        )

    return PaperVariableInventory(paper_id=paper_id, mentions=mentions, candidates=candidates)


def paper_variable_inventory_to_payload(inventory: PaperVariableInventory) -> dict[str, object]:
    """Serialize one inventory model as a JSON-friendly dictionary."""
    return inventory.model_dump(mode="json")


def _append_mention(
    *,
    mentions: list[VariableMention],
    seen_mentions: set[tuple[object, ...]],
    mention_counter: int,
    raw_label: str,
    normalized_label: str,
    source_type: str,
    section_id: str | None = None,
    heading: str | None = None,
    role_hint: str | None = None,
    paragraph_index: int | None = None,
    evidence_text: str | None = None,
    table_id: str | None = None,
    table_index: int | None = None,
    table_label: str | None = None,
    priority_weight: float,
    confidence: float | None,
) -> int:
    """Append one mention if it has not already been recorded."""
    cleaned_label = clean_text(raw_label)
    normalized_clean = _normalized_label(normalized_label or cleaned_label)
    if not cleaned_label or not normalized_clean:
        return mention_counter
    key = (
        cleaned_label,
        normalized_clean.lower(),
        source_type,
        section_id,
        paragraph_index,
        clean_text(evidence_text or ""),
        table_id,
        table_index,
    )
    if key in seen_mentions:
        return mention_counter
    seen_mentions.add(key)
    mentions.append(
        VariableMention(
            mention_id=f"mention_{mention_counter}",
            raw_label=cleaned_label,
            normalized_label=normalized_clean,
            source_type=source_type,
            section_id=section_id,
            heading=heading,
            role_hint=role_hint,
            paragraph_index=paragraph_index,
            evidence_text=clean_text(evidence_text or "") or None,
            table_id=table_id,
            table_index=table_index,
            table_label=table_label,
            priority_weight=round(priority_weight, 4),
            confidence=confidence,
            notes=[],
        )
    )
    return mention_counter + 1


def _candidate_key(value: str) -> str:
    """Return a conservative merge key for one label."""
    normalized = _normalized_label(value).lower()
    return normalized if len(normalized.replace(" ", "")) >= 3 else ""


def _normalized_label(value: str) -> str:
    """Normalize one label for cross-artifact comparison."""
    return normalize_label_text(clean_text(value))


def _term_in_normalized_text(normalized_term: str, normalized_text: str) -> bool:
    """Return whether a normalized term appears in normalized text with loose word boundaries."""
    compact_term = normalized_term.replace(" ", "")
    if len(compact_term) < 3:
        return False
    pattern = r"\b" + r"\s+".join(re.escape(part) for part in normalized_term.split()) + r"\b"
    return re.search(pattern, normalized_text) is not None


def _unique_preserving_order(values) -> list:
    """Return unique non-empty values while preserving order."""
    seen = set()
    ordered = []
    for value in values:
        if value in (None, "", []):
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
