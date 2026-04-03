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
                    and not bool(candidate.metadata.get("signals", {}).get("caption_match", False))
                    and len(candidate.raw_rows) >= 2
                    and _column_count(candidate) >= 3
                    and float(candidate.metadata.get("signals", {}).get("first_column_text_ratio", 0.0)) >= 0.8
                    and float(candidate.metadata.get("signals", {}).get("later_column_numeric_ratio", 0.0)) >= 0.75
                    and (anchor_cols := _column_count(current_anchor)) != 0
                    and abs(_column_count(candidate) - anchor_cols) <= 1
                ]
                if not matches:
                    break
                best_match = sorted(matches, key=lambda candidate: (-candidate.score, candidate.table_index))[0]
                selected[_candidate_key(best_match)] = best_match
                current_anchor = best_match
                next_page += 1
        selected_numbers = sorted(
            {
                table_number
                for candidate in selected.values()
                for table_number in [_caption_table_number(candidate)]
                if table_number is not None
            }
        )
        if len(selected_numbers) >= 2:
            threshold = max(0.55, confidence_threshold - 0.1)
            for missing_number in range(selected_numbers[0], selected_numbers[-1] + 1):
                if missing_number in selected_numbers or len(selected) >= max_candidates:
                    continue
                matches = [
                    candidate
                    for candidate in candidates
                    if _candidate_key(candidate) not in selected
                    and _caption_table_number(candidate) == missing_number
                ]
                above_threshold = [candidate for candidate in matches if candidate.score >= threshold]
                ranked = above_threshold or [
                    candidate
                    for candidate in matches
                    if bool(candidate.metadata.get("signals", {}).get("caption_match", False))
                    and (
                        (len(candidate.raw_rows) >= 2 and _column_count(candidate) >= 2)
                        or float(candidate.metadata.get("signals", {}).get("later_column_numeric_ratio", 0.0)) >= 0.75
                    )
                ]
                if not ranked:
                    continue
                best_match = sorted(
                    ranked,
                    key=lambda candidate: (-candidate.score, -_column_count(candidate), -len(candidate.raw_rows), candidate.page_num, candidate.table_index),
                )[0]
                if best_match.score < threshold:
                    best_match = best_match.model_copy(
                        update={
                            "metadata": {
                                **best_match.metadata,
                                "sequence_gap_recovered": True,
                                "sequence_gap_recovery_reason": "caption_matched_below_threshold",
                            }
                        }
                    )
                selected[_candidate_key(best_match)] = best_match
        return sorted(selected.values(), key=lambda candidate: (candidate.page_num, candidate.table_index))
    return ranked[:max_candidates]
