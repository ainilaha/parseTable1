# AGENTS.md

This repository contains a Python package for extracting and parsing **Table 1-style epidemiology tables** from PDF documents.

The system will ultimately:
1. Extract tables from PDFs.
2. Normalize them into a structured intermediate representation.
3. Parse them into variables, categorical levels, column roles, and values.
4. Use deterministic heuristics plus LLM assistance.
5. Output normalized structured representations of the table.

The full architecture specification is in:

docs/codex_build_spec.md

Agents should always read that file before implementing features.

---

# Project Goals

The package should:

- Detect Table 1 tables in epidemiology PDFs
- Extract the table grid
- Normalize row and column text
- Identify variables and categorical levels
- Identify column meanings
- Extract values into normalized long format

This is a **research-oriented parsing system**, not just a PDF table extractor.

---

# Architectural Principles

Agents must follow these design principles.

### Separation of responsibilities

Extraction, normalization, heuristics, LLM interpretation, and validation must be separate modules.

Never combine them into one step.

Pipeline structure should be:

PDF → ExtractedTable → NormalizedTable → ParsedTable

### Intermediate schema

All extractors must produce the same canonical structure:

ExtractedTable

Interpretation must operate on:

NormalizedTable

Final results must be:

ParsedTable

### Deterministic-first approach

Use rule-based parsing wherever possible.

The LLM is used only for semantic disambiguation, not for raw extraction.

### LLM safety rules

When the LLM is used:

- It must never invent rows or columns
- It must only refer to rows that exist in the table
- It must return structured JSON
- All results must be validated before being accepted

### Preserve raw data

Raw extracted cell values must never be discarded.

Normalized values must always preserve the original text.

---

# Coding Requirements

## Python version

Use:

Python 3.11+

## Dependencies

Allowed libraries include:

- pydantic v2
- pandas
- pdfplumber
- camelot
- tabula-py
- typer or argparse
- pytest

LLM integration must be abstracted behind an interface.

Do not hardcode one model provider.

## Typing

Use full type hints everywhere.

Public functions must include type hints.

## Data models

Structured data must use **Pydantic models**.

Avoid unstructured dictionaries where possible.

## File organization

Follow the structure defined in:

docs/codex_build_spec.md

Do not collapse modules into one file.

## Tests

All modules must be testable.

Write pytest tests for:

- schema validation
- normalization
- heuristic parsing

Extraction tests may use example PDFs in `examples/`.

---

# Development Strategy

The project is implemented in phases.

Agents must **only implement the requested phase** unless explicitly instructed otherwise.

Phases:

1. Project scaffold and schemas
2. PDF table extraction
3. Normalization layer
4. Heuristic parsing
5. LLM-assisted interpretation
6. Validation layer
7. CLI and exports
8. End-to-end pipeline

Do not skip phases.

---

# Style Guidelines

Prefer:

- small, focused modules
- pure functions where possible
- clear docstrings
- explicit data models

Avoid:

- global state
- large monolithic classes
- hidden side effects

---

# Error Handling

Extraction pipelines must fail gracefully.

If a table cannot be parsed:

- return a structured error
- do not crash the pipeline

---

# CLI

The package must expose a CLI called:

table1-parser

Example commands:

table1-parser extract path/to/paper.pdf

table1-parser parse path/to/paper.pdf

---

# Testing Requirements

Tests must exist for:

- schema validation
- normalization logic
- row classification heuristics
- variable grouping

End-to-end tests should parse example Table 1 PDFs.

---

# What Agents Should NOT Do

Do not:

- attempt to solve the entire pipeline in one module
- skip schema definitions
- rely entirely on LLM interpretation
- assume all tables have identical structure

Table 1 formats vary across journals.

The system must be robust to variation.

---

# First Task

When starting development, implement **Phase 1 only**:

- package scaffold
- schemas
- configuration module
- CLI stub
- minimal tests

Extraction and LLM logic will be implemented later.

