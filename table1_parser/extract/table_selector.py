"""Selection logic for scored table candidates."""

from __future__ import annotations

from table1_parser.extract.table_detector import DetectedTableCandidate


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
        return filtered[:max_candidates]
    return ranked[:max_candidates]
