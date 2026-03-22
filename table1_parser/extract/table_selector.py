"""Selection logic for scored table candidates."""

from __future__ import annotations

from table1_parser.extract.table_detector import DetectedTableCandidate


def _candidate_key(candidate: DetectedTableCandidate) -> tuple[int, int]:
    """Return a stable candidate key for deduplication."""
    return (candidate.page_num, candidate.table_index)


def _column_count(candidate: DetectedTableCandidate) -> int:
    """Return the width of the candidate grid."""
    return max((len(row) for row in candidate.raw_rows), default=0)


def _caption_table_number(candidate: DetectedTableCandidate) -> int | None:
    """Return the detected caption table number when present."""
    signals = candidate.metadata.get("signals", {})
    value = signals.get("caption_table_number")
    return value if isinstance(value, int) else None


def _is_likely_continuation(
    candidate: DetectedTableCandidate,
    anchor: DetectedTableCandidate,
) -> bool:
    """Return whether an uncaptioned candidate likely continues a nearby table."""
    signals = candidate.metadata.get("signals", {})
    if bool(signals.get("caption_match", False)):
        return False
    if len(candidate.raw_rows) < 2 or _column_count(candidate) < 3:
        return False
    if float(signals.get("first_column_text_ratio", 0.0)) < 0.8:
        return False
    if float(signals.get("later_column_numeric_ratio", 0.0)) < 0.75:
        return False
    anchor_cols = _column_count(anchor)
    candidate_cols = _column_count(candidate)
    if anchor_cols == 0 or abs(candidate_cols - anchor_cols) > 1:
        return False
    return True


def _gap_fill_threshold(confidence_threshold: float) -> float:
    """Return a slightly relaxed threshold for numbered gaps inside a selected run."""
    return max(0.55, confidence_threshold - 0.1)


def _is_minimally_table_like(candidate: DetectedTableCandidate) -> bool:
    """Return whether a discarded captioned candidate is still plausible enough to recover."""
    signals = candidate.metadata.get("signals", {})
    if not bool(signals.get("caption_match", False)):
        return False
    if len(candidate.raw_rows) >= 2 and _column_count(candidate) >= 2:
        return True
    return float(signals.get("later_column_numeric_ratio", 0.0)) >= 0.75


def _recover_gap_candidate(
    matches: list[DetectedTableCandidate],
    threshold: float,
) -> DetectedTableCandidate | None:
    """Pick the best gap-filling candidate, preferring threshold-passing matches first."""
    above_threshold = [candidate for candidate in matches if candidate.score >= threshold]
    ranked = above_threshold or [candidate for candidate in matches if _is_minimally_table_like(candidate)]
    if not ranked:
        return None
    best_match = sorted(
        ranked,
        key=lambda candidate: (-candidate.score, -_column_count(candidate), -len(candidate.raw_rows), candidate.page_num, candidate.table_index),
    )[0]
    if best_match.score >= threshold:
        return best_match
    return best_match.model_copy(
        update={
            "metadata": {
                **best_match.metadata,
                "sequence_gap_recovered": True,
                "sequence_gap_recovery_reason": "caption_matched_below_threshold",
            }
        }
    )


def _fill_caption_number_gaps(
    selected: dict[tuple[int, int], DetectedTableCandidate],
    candidates: list[DetectedTableCandidate],
    max_candidates: int,
    confidence_threshold: float,
) -> None:
    """Add missing numbered tables between already selected captioned tables when available."""
    selected_numbers = sorted(
        {
            table_number
            for candidate in selected.values()
            for table_number in [_caption_table_number(candidate)]
            if table_number is not None
        }
    )
    if len(selected_numbers) < 2:
        return

    threshold = _gap_fill_threshold(confidence_threshold)
    for missing_number in range(selected_numbers[0], selected_numbers[-1] + 1):
        if missing_number in selected_numbers or len(selected) >= max_candidates:
            continue
        matches = [
            candidate
            for candidate in candidates
            if _candidate_key(candidate) not in selected
            and _caption_table_number(candidate) == missing_number
        ]
        best_match = _recover_gap_candidate(matches, threshold)
        if best_match is None:
            continue
        selected[_candidate_key(best_match)] = best_match


def select_top_candidates(
    candidates: list[DetectedTableCandidate],
    max_candidates: int,
    confidence_threshold: float,
) -> list[DetectedTableCandidate]:
    """Select the highest scoring table candidates for extraction output."""
    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.score, candidate.page_num, candidate.table_index),
    )
    filtered = [candidate for candidate in ranked if candidate.score >= confidence_threshold]
    if filtered:
        selected: dict[tuple[int, int], DetectedTableCandidate] = {
            _candidate_key(candidate): candidate for candidate in filtered[:max_candidates]
        }
        candidates_by_page: dict[int, list[DetectedTableCandidate]] = {}
        for candidate in candidates:
            candidates_by_page.setdefault(candidate.page_num, []).append(candidate)

        continuation_threshold = max(0.5, confidence_threshold - 0.2)
        ordered_anchors = sorted(selected.values(), key=lambda candidate: (candidate.page_num, candidate.table_index))
        for anchor in ordered_anchors:
            current_anchor = anchor
            next_page = anchor.page_num + 1
            while len(selected) < max_candidates and next_page in candidates_by_page:
                matches = [
                    candidate
                    for candidate in candidates_by_page[next_page]
                    if _candidate_key(candidate) not in selected
                    and candidate.score >= continuation_threshold
                    and _is_likely_continuation(candidate, current_anchor)
                ]
                if not matches:
                    break
                best_match = sorted(matches, key=lambda candidate: (-candidate.score, candidate.table_index))[0]
                selected[_candidate_key(best_match)] = best_match
                current_anchor = best_match
                next_page += 1
        _fill_caption_number_gaps(selected, candidates, max_candidates, confidence_threshold)
        return sorted(selected.values(), key=lambda candidate: (candidate.page_num, candidate.table_index))
    return ranked[:max_candidates]
