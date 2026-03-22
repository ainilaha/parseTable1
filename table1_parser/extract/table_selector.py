"""Selection logic for scored table candidates."""

from __future__ import annotations

from table1_parser.extract.table_detector import DetectedTableCandidate


def _candidate_key(candidate: DetectedTableCandidate) -> tuple[int, int]:
    """Return a stable candidate key for deduplication."""
    return (candidate.page_num, candidate.table_index)


def _column_count(candidate: DetectedTableCandidate) -> int:
    """Return the width of the candidate grid."""
    return max((len(row) for row in candidate.raw_rows), default=0)


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
        return sorted(selected.values(), key=lambda candidate: (candidate.page_num, candidate.table_index))
    return ranked[:max_candidates]
