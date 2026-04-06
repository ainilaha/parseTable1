"""Selection logic for scored table candidates."""

from __future__ import annotations

from table1_parser.extract.table_detector import DetectedTableCandidate


def _candidate_key(candidate: DetectedTableCandidate) -> tuple[int, int]:
    """Return a stable candidate key for deduplication."""
    return (candidate.page_num, candidate.table_index)


def select_top_candidates(
    candidates: list[DetectedTableCandidate],
    max_candidates: int,
    confidence_threshold: float,
) -> list[DetectedTableCandidate]:
    """Return extracted candidates in stable order without dropping them for score or count."""
    del max_candidates, confidence_threshold
    selected: dict[tuple[int, int], DetectedTableCandidate] = {}
    for candidate in sorted(
        candidates,
        key=lambda candidate: (candidate.page_num, candidate.table_index, -candidate.score),
    ):
        key = _candidate_key(candidate)
        existing = selected.get(key)
        if existing is None or candidate.score > existing.score:
            selected[key] = candidate
    return sorted(selected.values(), key=lambda candidate: (candidate.page_num, candidate.table_index))
