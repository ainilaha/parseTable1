Read:

AGENTS.md  
docs/codex_build_spec.md  

Implement Phase 2 only.

Goal: implement raw PDF table extraction.

Do NOT implement normalization or parsing yet.
Do not attempt to interpret the table structure yet.

---

# Phase 2 tasks

Implement the extraction layer.

Create these modules:

table1_parser/extract/base.py  
table1_parser/extract/pdf_loader.py  
table1_parser/extract/table_detector.py  
table1_parser/extract/table_selector.py  
table1_parser/extract/pymupdf4llm_extractor.py  

Camelot and Tabula backends may be stubs for now.

---

# Extractor interface

Define a base extractor interface:

extract(pdf_path: str) -> list[ExtractedTable]

Each extractor must return ExtractedTable objects defined in schemas.

---

# PyMuPDF4LLM extractor

Implement a working backend using PyMuPDF4LLM.

Requirements:

- detect tables using PyMuPDF4LLM table extraction
- convert table grid into TableCell objects
- assign row_idx and col_idx
- populate ExtractedTable fields
- capture page number

---

# Table detection

Implement simple heuristics to identify likely Table 1 tables.

Score candidate tables based on:

- caption or nearby text contains "Table 1"
- first column mostly text
- later columns mostly numeric
- rectangular grid

Return top candidates.

---

# CLI

Update CLI command:

table1-parser extract path/to/file.pdf

Output JSON of ExtractedTable.

---

# Tests

Add tests for:

- ExtractedTable creation
- extractor returning tables
- cell indexing
- JSON serialization

Use sample PDFs in examples/.

---

# Non-goals for Phase 2

Do NOT implement:

- normalization
- row parsing
- column interpretation
- LLM integration
- value extraction

Only extraction.

---

# Deliverable

After Phase 2:

Running

table1-parser extract paper.pdf

should return JSON representing extracted tables.
