"""Deterministic routing of normalized tables into semantic families."""

from __future__ import annotations

import re

from table1_parser.heuristics.column_role_detector import detect_column_roles
from table1_parser.heuristics.value_pattern_detector import detect_value_pattern
from table1_parser.heuristics.variable_grouper import group_variable_blocks
from table1_parser.normalize.cleaner import clean_text
from table1_parser.schemas import NormalizedTable, TableProfile
from table1_parser.validation.table_profile import validate_table_profile


DESCRIPTIVE_TEXT_PATTERN = re.compile(
    r"\b(?:baseline|characteristics?|clinical characteristics|demographic)\b",
    re.IGNORECASE,
)
ESTIMATE_TEXT_PATTERN = re.compile(
    r"\b(?:hazard ratio|odds ratio|relative risk|risk ratio|association|regression|multivariable|cox|logistic|linear)\b",
    re.IGNORECASE,
)
MODEL_HEADER_PATTERN = re.compile(r"\b(?:adjusted|unadjusted|model\s*\d+)\b", re.IGNORECASE)
ESTIMATE_HEADER_PATTERN = re.compile(
    r"\b(?:hazard ratio|odds ratio|relative risk|risk ratio|95%\s*ci|confidence interval|hr\b|or\b|rr\b)\b",
    re.IGNORECASE,
)
INLINE_INTERVAL_PATTERN = re.compile(
    r"^-?\d+(?:\.\d+)?\s*[\(\[]\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*[\)\]]$"
)


def build_table_profile(table: NormalizedTable) -> TableProfile:
    """Classify one normalized table into a supported semantic family."""
    evidence: list[str] = []
    descriptive_score = 0
    estimate_score = 0

    title_caption_text = clean_text(" ".join(part for part in [table.title or "", table.caption or ""] if part))
    header_text = clean_text(" ".join(_header_labels(table)))
    all_context_text = clean_text(" ".join(part for part in [title_caption_text, header_text] if part))

    if DESCRIPTIVE_TEXT_PATTERN.search(title_caption_text):
        descriptive_score += 2
        evidence.append("title_or_caption_mentions_characteristics")
    if ESTIMATE_TEXT_PATTERN.search(all_context_text):
        estimate_score += 2
        evidence.append("title_caption_or_header_mentions_estimate_metric")
    if ESTIMATE_HEADER_PATTERN.search(header_text):
        estimate_score += 1
        evidence.append("header_mentions_estimate_metric_or_ci")
    if MODEL_HEADER_PATTERN.search(header_text):
        estimate_score += 1
        evidence.append("header_mentions_model_or_adjustment")

    pattern_counts = _pattern_counts(table)
    descriptive_pattern_total = sum(
        pattern_counts.get(name, 0) for name in ("count_pct", "mean_sd", "median_iqr", "n_only")
    )
    if descriptive_pattern_total >= 2:
        descriptive_score += 1
        evidence.append("body_contains_descriptive_summary_patterns")
    if pattern_counts.get("count_pct", 0) >= 2:
        descriptive_score += 1
        evidence.append("body_contains_multiple_count_percent_cells")

    variable_blocks = group_variable_blocks(table)
    if any(block.level_row_indices for block in variable_blocks):
        descriptive_score += 2
        evidence.append("row_structure_contains_parent_level_blocks")

    column_roles = detect_column_roles(table)
    if any(role.role in {"overall", "group", "comparison_group"} for role in column_roles):
        descriptive_score += 1
        evidence.append("header_contains_group_or_overall_columns")
    p_value_column_count = sum(role.role == "p_value" for role in column_roles)

    inline_interval_count = _inline_interval_count(table)
    if inline_interval_count >= 2:
        estimate_score += 2
        evidence.append("body_contains_multiple_inline_estimate_intervals")

    p_value_like_count = pattern_counts.get("p_value", 0)
    if p_value_column_count >= 1 and p_value_like_count >= 2:
        estimate_score += 1
        evidence.append("p_value_column_matches_p_value_like_cells")

    if estimate_score >= 4 and estimate_score > descriptive_score:
        family = "estimate_results"
    elif descriptive_score >= 3 and descriptive_score >= estimate_score:
        family = "descriptive_characteristics"
    else:
        family = "unknown"
        if not evidence:
            evidence.append("insufficient_family_evidence")

    profile = TableProfile(
        table_id=table.table_id,
        title=table.title,
        caption=table.caption,
        table_family=family,
        should_run_llm_semantics=(family == "descriptive_characteristics"),
        family_confidence=_family_confidence(descriptive_score, estimate_score, family),
        evidence=evidence,
        notes=[],
    )
    return validate_table_profile(profile)


def build_table_profiles(tables: list[NormalizedTable]) -> list[TableProfile]:
    """Build deterministic route decisions for a list of normalized tables."""
    return [build_table_profile(table) for table in tables]


def table_profiles_to_payload(profiles: list[TableProfile]) -> list[dict[str, object]]:
    """Serialize table profiles as JSON-friendly dictionaries."""
    return [profile.model_dump(mode="json") for profile in profiles]


def _header_labels(table: NormalizedTable) -> list[str]:
    """Return one cleaned header label per visible data column."""
    cleaned_rows = table.metadata.get("cleaned_rows", [])
    if not isinstance(cleaned_rows, list):
        return []
    header_rows = [cleaned_rows[row_idx] for row_idx in table.header_rows if row_idx < len(cleaned_rows)]
    labels: list[str] = []
    for col_idx in range(table.n_cols):
        parts = [row[col_idx] for row in header_rows if col_idx < len(row) and clean_text(str(row[col_idx]))]
        label = clean_text(" ".join(str(part) for part in parts))
        if label:
            labels.append(label)
    return labels


def _pattern_counts(table: NormalizedTable) -> dict[str, int]:
    """Count recognized value-pattern families across the normalized body."""
    counts: dict[str, int] = {}
    for row_view in table.row_views:
        for raw_value in row_view.raw_cells[1:]:
            cleaned = clean_text(raw_value)
            if not cleaned:
                continue
            pattern = detect_value_pattern(raw_value).pattern
            counts[pattern] = counts.get(pattern, 0) + 1
    return counts


def _inline_interval_count(table: NormalizedTable) -> int:
    """Count body cells that look like one estimate accompanied by a two-number interval."""
    count = 0
    for row_view in table.row_views:
        for raw_value in row_view.raw_cells[1:]:
            if INLINE_INTERVAL_PATTERN.fullmatch(clean_text(raw_value)):
                count += 1
    return count


def _family_confidence(descriptive_score: int, estimate_score: int, family: str) -> float:
    """Turn simple routing scores into a bounded confidence value."""
    if family == "descriptive_characteristics":
        return min(0.98, round(0.55 + 0.08 * descriptive_score + 0.03 * max(0, descriptive_score - estimate_score), 4))
    if family == "estimate_results":
        return min(0.98, round(0.55 + 0.08 * estimate_score + 0.03 * max(0, estimate_score - descriptive_score), 4))
    best_score = max(descriptive_score, estimate_score)
    return min(0.75, round(0.35 + 0.05 * best_score, 4))
