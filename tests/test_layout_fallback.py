"""Backend-agnostic layout fallback tests."""

from __future__ import annotations

from table1_parser.extract.layout_fallback import (
    _build_rows_from_line_segment,
    _restore_word_text,
    build_text_layout_candidates,
)


def test_build_text_layout_candidates_detects_unruled_table() -> None:
    """Layout fallback should reconstruct a captioned unruled table from words alone."""
    words = [
        {"text": "Table1", "x0": 50.0, "x1": 90.0, "top": 60.0, "bottom": 68.0},
        {"text": "Baselinecharacteristics", "x0": 50.0, "x1": 220.0, "top": 72.0, "bottom": 80.0},
        {"text": "Q1", "x0": 240.0, "x1": 250.0, "top": 86.0, "bottom": 94.0},
        {"text": "Q2", "x0": 300.0, "x1": 310.0, "top": 86.0, "bottom": 94.0},
        {"text": "Variable", "x0": 50.0, "x1": 110.0, "top": 96.0, "bottom": 104.0},
        {"text": "All", "x0": 180.0, "x1": 195.0, "top": 96.0, "bottom": 104.0},
        {"text": "0.12", "x0": 240.0, "x1": 260.0, "top": 96.0, "bottom": 104.0},
        {"text": "0.13-0.14", "x0": 300.0, "x1": 340.0, "top": 96.0, "bottom": 104.0},
        {"text": "Age", "x0": 50.0, "x1": 70.0, "top": 110.0, "bottom": 118.0},
        {"text": "52.1", "x0": 180.0, "x1": 200.0, "top": 110.0, "bottom": 118.0},
        {"text": "49.8", "x0": 240.0, "x1": 260.0, "top": 110.0, "bottom": 118.0},
        {"text": "53.7", "x0": 300.0, "x1": 320.0, "top": 110.0, "bottom": 118.0},
    ]

    candidates = build_text_layout_candidates(page_num=1, page_text="Table1\nBaselinecharacteristics", words=words)

    assert len(candidates) == 1
    assert candidates[0].caption == "Table1\nBaselinecharacteristics"
    assert candidates[0].metadata["layout_source"] == "text_positions"
    assert candidates[0].raw_rows[0][1:3] == ["Q1", "Q2"]


def test_text_layout_fallback_restores_spaces_in_collapsed_first_column_tokens() -> None:
    """Fallback extraction should restore readable spacing from char gaps in first-column labels."""
    words = [
        {"text": "Q1", "x0": 220.0, "x1": 235.0, "top": 96.0, "bottom": 104.0},
        {"text": "Q2", "x0": 280.0, "x1": 295.0, "top": 96.0, "bottom": 104.0},
        {"text": "Familypoverty-incomeratio,n(%)", "x0": 50.0, "x1": 150.0, "top": 110.0, "bottom": 118.0},
        {"text": "100", "x0": 220.0, "x1": 235.0, "top": 110.0, "bottom": 118.0},
        {"text": "120", "x0": 280.0, "x1": 295.0, "top": 110.0, "bottom": 118.0},
    ]
    chars = [
        {"text": "F", "x0": 50.0, "x1": 53.0, "top": 110.0, "bottom": 118.0},
        {"text": "a", "x0": 53.0, "x1": 56.0, "top": 110.0, "bottom": 118.0},
        {"text": "m", "x0": 56.0, "x1": 60.0, "top": 110.0, "bottom": 118.0},
        {"text": "i", "x0": 60.0, "x1": 61.5, "top": 110.0, "bottom": 118.0},
        {"text": "l", "x0": 61.5, "x1": 63.0, "top": 110.0, "bottom": 118.0},
        {"text": "y", "x0": 63.0, "x1": 66.0, "top": 110.0, "bottom": 118.0},
        {"text": "p", "x0": 69.0, "x1": 72.0, "top": 110.0, "bottom": 118.0},
        {"text": "o", "x0": 72.0, "x1": 75.0, "top": 110.0, "bottom": 118.0},
        {"text": "v", "x0": 75.0, "x1": 78.0, "top": 110.0, "bottom": 118.0},
        {"text": "e", "x0": 78.0, "x1": 81.0, "top": 110.0, "bottom": 118.0},
        {"text": "r", "x0": 81.0, "x1": 83.0, "top": 110.0, "bottom": 118.0},
        {"text": "t", "x0": 83.0, "x1": 85.0, "top": 110.0, "bottom": 118.0},
        {"text": "y", "x0": 85.0, "x1": 88.0, "top": 110.0, "bottom": 118.0},
        {"text": "-", "x0": 88.0, "x1": 90.0, "top": 110.0, "bottom": 118.0},
        {"text": "i", "x0": 90.0, "x1": 91.5, "top": 110.0, "bottom": 118.0},
        {"text": "n", "x0": 91.5, "x1": 94.5, "top": 110.0, "bottom": 118.0},
        {"text": "c", "x0": 94.5, "x1": 97.5, "top": 110.0, "bottom": 118.0},
        {"text": "o", "x0": 97.5, "x1": 100.5, "top": 110.0, "bottom": 118.0},
        {"text": "m", "x0": 100.5, "x1": 104.5, "top": 110.0, "bottom": 118.0},
        {"text": "e", "x0": 104.5, "x1": 107.5, "top": 110.0, "bottom": 118.0},
        {"text": "r", "x0": 110.5, "x1": 112.5, "top": 110.0, "bottom": 118.0},
        {"text": "a", "x0": 112.5, "x1": 115.5, "top": 110.0, "bottom": 118.0},
        {"text": "t", "x0": 115.5, "x1": 117.5, "top": 110.0, "bottom": 118.0},
        {"text": "i", "x0": 117.5, "x1": 119.0, "top": 110.0, "bottom": 118.0},
        {"text": "o", "x0": 119.0, "x1": 122.0, "top": 110.0, "bottom": 118.0},
        {"text": ",", "x0": 122.0, "x1": 123.5, "top": 110.0, "bottom": 118.0},
        {"text": "n", "x0": 126.5, "x1": 129.5, "top": 110.0, "bottom": 118.0},
        {"text": "(", "x0": 132.5, "x1": 134.0, "top": 110.0, "bottom": 118.0},
        {"text": "%", "x0": 134.0, "x1": 138.0, "top": 110.0, "bottom": 118.0},
        {"text": ")", "x0": 138.0, "x1": 139.5, "top": 110.0, "bottom": 118.0},
    ]

    rows = _build_rows_from_line_segment([{"top": 96.0, "bottom": 104.0, "words": words[:2]}, {"top": 110.0, "bottom": 118.0, "words": words[2:]}], page_chars=chars)

    assert rows[1][0].startswith("Family poverty-income ratio, n (%)")


def test_text_layout_fallback_restores_short_collapsed_category_labels() -> None:
    """Fallback extraction should restore spaces in shorter first-column category labels."""
    other_word = {"text": "Otherrace", "x0": 50.0, "x1": 96.0, "top": 98.0, "bottom": 106.0}
    mexican_word = {"text": "MexicanAmerican", "x0": 50.0, "x1": 122.0, "top": 112.0, "bottom": 120.0}
    chars = [
        {"text": "O", "x0": 50.0, "x1": 54.0, "top": 98.0, "bottom": 106.0},
        {"text": "t", "x0": 54.0, "x1": 56.0, "top": 98.0, "bottom": 106.0},
        {"text": "h", "x0": 56.0, "x1": 60.0, "top": 98.0, "bottom": 106.0},
        {"text": "e", "x0": 60.0, "x1": 64.0, "top": 98.0, "bottom": 106.0},
        {"text": "r", "x0": 64.0, "x1": 67.0, "top": 98.0, "bottom": 106.0},
        {"text": "r", "x0": 70.0, "x1": 73.0, "top": 98.0, "bottom": 106.0},
        {"text": "a", "x0": 73.0, "x1": 77.0, "top": 98.0, "bottom": 106.0},
        {"text": "c", "x0": 77.0, "x1": 81.0, "top": 98.0, "bottom": 106.0},
        {"text": "e", "x0": 81.0, "x1": 85.0, "top": 98.0, "bottom": 106.0},
        {"text": "M", "x0": 50.0, "x1": 56.0, "top": 112.0, "bottom": 120.0},
        {"text": "e", "x0": 56.0, "x1": 60.0, "top": 112.0, "bottom": 120.0},
        {"text": "x", "x0": 60.0, "x1": 64.0, "top": 112.0, "bottom": 120.0},
        {"text": "i", "x0": 64.0, "x1": 66.0, "top": 112.0, "bottom": 120.0},
        {"text": "c", "x0": 66.0, "x1": 70.0, "top": 112.0, "bottom": 120.0},
        {"text": "a", "x0": 70.0, "x1": 74.0, "top": 112.0, "bottom": 120.0},
        {"text": "n", "x0": 74.0, "x1": 78.0, "top": 112.0, "bottom": 120.0},
        {"text": "A", "x0": 81.0, "x1": 87.0, "top": 112.0, "bottom": 120.0},
        {"text": "m", "x0": 87.0, "x1": 93.0, "top": 112.0, "bottom": 120.0},
        {"text": "e", "x0": 93.0, "x1": 97.0, "top": 112.0, "bottom": 120.0},
        {"text": "r", "x0": 97.0, "x1": 100.0, "top": 112.0, "bottom": 120.0},
        {"text": "i", "x0": 100.0, "x1": 102.0, "top": 112.0, "bottom": 120.0},
        {"text": "c", "x0": 102.0, "x1": 106.0, "top": 112.0, "bottom": 120.0},
        {"text": "a", "x0": 106.0, "x1": 110.0, "top": 112.0, "bottom": 120.0},
        {"text": "n", "x0": 110.0, "x1": 114.0, "top": 112.0, "bottom": 120.0},
    ]
    lines = [
        {"top": 84.0, "bottom": 92.0, "words": [{"text": "Race", "x0": 50.0, "x1": 90.0, "top": 84.0, "bottom": 92.0}, {"text": "Overall", "x0": 220.0, "x1": 260.0, "top": 84.0, "bottom": 92.0}]},
        {"top": 98.0, "bottom": 106.0, "words": [other_word, {"text": "10", "x0": 220.0, "x1": 232.0, "top": 98.0, "bottom": 106.0}]},
        {"top": 112.0, "bottom": 120.0, "words": [mexican_word, {"text": "12", "x0": 220.0, "x1": 232.0, "top": 112.0, "bottom": 120.0}]},
    ]

    rows = _build_rows_from_line_segment(lines, page_chars=chars)

    assert _restore_word_text(other_word, chars) == "Other race"
    assert _restore_word_text(mexican_word, chars) == "Mexican American"
    assert rows[1][0].startswith("Other race")
    assert rows[2][0].startswith("Mexican American")


def test_text_layout_fallback_restores_shifted_label_column_tokens() -> None:
    """Collapsed labels should still be restored when extraction shifts the row-label column right by one."""
    chars = [
        {"text": "O", "x0": 132.0, "x1": 136.0, "top": 98.0, "bottom": 106.0},
        {"text": "t", "x0": 136.0, "x1": 138.0, "top": 98.0, "bottom": 106.0},
        {"text": "h", "x0": 138.0, "x1": 142.0, "top": 98.0, "bottom": 106.0},
        {"text": "e", "x0": 142.0, "x1": 146.0, "top": 98.0, "bottom": 106.0},
        {"text": "r", "x0": 146.0, "x1": 149.0, "top": 98.0, "bottom": 106.0},
        {"text": "r", "x0": 152.0, "x1": 155.0, "top": 98.0, "bottom": 106.0},
        {"text": "a", "x0": 155.0, "x1": 159.0, "top": 98.0, "bottom": 106.0},
        {"text": "c", "x0": 159.0, "x1": 163.0, "top": 98.0, "bottom": 106.0},
        {"text": "e", "x0": 163.0, "x1": 167.0, "top": 98.0, "bottom": 106.0},
        {"text": "M", "x0": 132.0, "x1": 138.0, "top": 112.0, "bottom": 120.0},
        {"text": "e", "x0": 138.0, "x1": 142.0, "top": 112.0, "bottom": 120.0},
        {"text": "x", "x0": 142.0, "x1": 146.0, "top": 112.0, "bottom": 120.0},
        {"text": "i", "x0": 146.0, "x1": 148.0, "top": 112.0, "bottom": 120.0},
        {"text": "c", "x0": 148.0, "x1": 152.0, "top": 112.0, "bottom": 120.0},
        {"text": "a", "x0": 152.0, "x1": 156.0, "top": 112.0, "bottom": 120.0},
        {"text": "n", "x0": 156.0, "x1": 160.0, "top": 112.0, "bottom": 120.0},
        {"text": "A", "x0": 163.0, "x1": 169.0, "top": 112.0, "bottom": 120.0},
        {"text": "m", "x0": 169.0, "x1": 175.0, "top": 112.0, "bottom": 120.0},
        {"text": "e", "x0": 175.0, "x1": 179.0, "top": 112.0, "bottom": 120.0},
        {"text": "r", "x0": 179.0, "x1": 182.0, "top": 112.0, "bottom": 120.0},
        {"text": "i", "x0": 182.0, "x1": 184.0, "top": 112.0, "bottom": 120.0},
        {"text": "c", "x0": 184.0, "x1": 188.0, "top": 112.0, "bottom": 120.0},
        {"text": "a", "x0": 188.0, "x1": 192.0, "top": 112.0, "bottom": 120.0},
        {"text": "n", "x0": 192.0, "x1": 196.0, "top": 112.0, "bottom": 120.0},
    ]
    rows = _build_rows_from_line_segment(
        [
            {"top": 84.0, "bottom": 92.0, "words": [{"text": "Overall", "x0": 220.0, "x1": 260.0, "top": 84.0, "bottom": 92.0}, {"text": "Cases", "x0": 300.0, "x1": 340.0, "top": 84.0, "bottom": 92.0}]},
            {"top": 98.0, "bottom": 106.0, "words": [{"text": "Otherrace", "x0": 132.0, "x1": 178.0, "top": 98.0, "bottom": 106.0}, {"text": "10", "x0": 220.0, "x1": 232.0, "top": 98.0, "bottom": 106.0}, {"text": "11", "x0": 300.0, "x1": 312.0, "top": 98.0, "bottom": 106.0}]},
            {"top": 112.0, "bottom": 120.0, "words": [{"text": "MexicanAmerican", "x0": 132.0, "x1": 204.0, "top": 112.0, "bottom": 120.0}, {"text": "12", "x0": 220.0, "x1": 232.0, "top": 112.0, "bottom": 120.0}, {"text": "13", "x0": 300.0, "x1": 312.0, "top": 112.0, "bottom": 120.0}]},
        ],
        page_chars=chars,
    )

    assert rows[1][0].startswith("Other race")
    assert rows[2][0].startswith("Mexican American")
