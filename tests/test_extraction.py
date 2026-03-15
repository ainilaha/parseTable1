"""Extraction layer tests for Phase 2."""

from __future__ import annotations

import json
import sys
from types import ModuleType

from table1_parser import cli
from table1_parser.extract.pdfplumber_extractor import PDFPlumberExtractor
from table1_parser.extract.table_detector import (
    DetectedTableCandidate,
    detect_table_candidates,
    score_candidate,
)


class FakeCroppedPage:
    """Simple cropped-page test double."""

    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        """Return the cropped text block."""
        return self._text


class FakeTable:
    """Simple pdfplumber table test double."""

    def __init__(
        self,
        rows: list[list[str]],
        bbox: tuple[float, float, float, float] = (10.0, 100.0, 300.0, 220.0),
    ) -> None:
        self._rows = rows
        self.bbox = bbox

    def extract(self) -> list[list[str]]:
        """Return the extracted raw rows."""
        return self._rows


class FakePage:
    """Simple pdfplumber page test double."""

    width = 612.0

    def __init__(
        self,
        text: str,
        tables: list[FakeTable],
        cropped_text: str | None = None,
        words: list[dict[str, object]] | None = None,
    ) -> None:
        self._text = text
        self._tables = tables
        self._cropped_text = cropped_text or text
        self._words = words or []

    def extract_text(self) -> str:
        """Return page text."""
        return self._text

    def find_tables(self) -> list[FakeTable]:
        """Return preconfigured tables."""
        return self._tables

    def crop(self, _: tuple[float, float, float, float]) -> FakeCroppedPage:
        """Return a cropped page region."""
        return FakeCroppedPage(self._cropped_text)

    def extract_words(self, **_: object) -> list[dict[str, object]]:
        """Return positioned words for text-layout fallback extraction."""
        return self._words


class FakePDF:
    """Simple pdfplumber PDF test double."""

    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages

    def __enter__(self) -> FakePDF:
        """Enter the fake context manager."""
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Exit the fake context manager."""
        return None


def _install_fake_pdfplumber(monkeypatch, pdf: FakePDF) -> None:
    """Install a minimal fake pdfplumber module for a test case."""
    module = ModuleType("pdfplumber")
    module.open = lambda _: pdf
    monkeypatch.setitem(sys.modules, "pdfplumber", module)


def test_score_candidate_prefers_table1_like_layout() -> None:
    """Detection should reward Table 1 captions and text-first layouts."""
    candidate = DetectedTableCandidate(
        page_num=1,
        table_index=0,
        raw_rows=[
            ["Variable", "Overall", "P"],
            ["Age", "52.1", "0.03"],
            ["BMI", "27.4", "0.10"],
        ],
        caption="Table 1. Baseline characteristics",
        page_text="Table 1. Baseline characteristics",
        metadata={"is_rectangular": True},
    )

    scored = score_candidate(candidate)

    assert scored.score >= 0.9
    assert scored.metadata["signals"]["caption_match"] is True


def test_detect_table_candidates_scores_tables_on_a_page() -> None:
    """Table detection should score candidates extracted from a PDF page."""
    pdf = FakePDF(
        pages=[
            FakePage(
                text="Table 1. Baseline characteristics",
                tables=[FakeTable([["Variable", "Overall"], ["Age", "52.1"]])],
            )
        ]
    )

    candidates = detect_table_candidates(pdf)

    assert len(candidates) == 1
    assert candidates[0].page_num == 1
    assert candidates[0].score > 0.7


def test_pdfplumber_extractor_returns_indexed_cells(tmp_path, monkeypatch) -> None:
    """The extractor should convert raw grid cells into indexed TableCell objects."""
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")
    fake_pdf = FakePDF(
        pages=[
            FakePage(
                text="Table 1. Baseline characteristics",
                cropped_text="Table 1. Baseline characteristics",
                tables=[
                    FakeTable(
                        [
                            ["Variable", "Overall", "P"],
                            ["Age", "52.1", "0.03"],
                            ["Male", "34", "0.10"],
                        ]
                    )
                ],
            )
        ]
    )
    _install_fake_pdfplumber(monkeypatch, fake_pdf)

    extractor = PDFPlumberExtractor(max_candidates=3, heuristic_confidence_threshold=0.0)
    tables = extractor.extract(str(pdf_path))

    assert len(tables) == 1
    assert tables[0].n_rows == 3
    assert tables[0].n_cols == 3
    assert tables[0].cells[0].row_idx == 0
    assert tables[0].cells[0].col_idx == 0
    assert tables[0].cells[4].text == "52.1"
    assert tables[0].page_num == 1
    assert tables[0].extraction_backend == "pdfplumber"


def test_cli_extract_outputs_json(tmp_path, monkeypatch, capsys) -> None:
    """The extract CLI should print serialized ExtractedTable JSON."""
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")
    fake_pdf = FakePDF(
        pages=[
            FakePage(
                text="Table 1. Baseline characteristics",
                cropped_text="Table 1. Baseline characteristics",
                tables=[FakeTable([["Variable", "Overall"], ["Age", "52.1"]])],
            )
        ]
    )
    _install_fake_pdfplumber(monkeypatch, fake_pdf)

    exit_code = cli.main(["extract", str(pdf_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload[0]["page_num"] == 1
    assert payload[0]["cells"][0]["text"] == "Variable"


def test_text_layout_fallback_detects_unruled_table(tmp_path, monkeypatch) -> None:
    """The detector should reconstruct a table from positioned words when no grid is found."""
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder")
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
    fake_pdf = FakePDF(
        pages=[
            FakePage(
                text="Table1\nBaselinecharacteristics\nQ1 Q2",
                cropped_text="Table1\nBaselinecharacteristics",
                tables=[],
                words=words,
            )
        ]
    )
    _install_fake_pdfplumber(monkeypatch, fake_pdf)

    extractor = PDFPlumberExtractor(max_candidates=3, heuristic_confidence_threshold=0.0)
    tables = extractor.extract(str(pdf_path))

    assert len(tables) == 1
    assert tables[0].title == "Table1"
    assert tables[0].caption == "Table1 Baselinecharacteristics"
    assert tables[0].n_rows == 3
    assert tables[0].n_cols == 4
    cell_map = {(cell.row_idx, cell.col_idx): cell.text for cell in tables[0].cells}
    assert cell_map[(0, 1)] == "Q1"
    assert cell_map[(0, 2)] == "Q2"
    assert tables[0].metadata["layout_source"] == "text_positions"
