# Paper Markdown Spec

This document defines the intent of `paper_markdown.md`, the paper-level markdown artifact written by `table1-parser parse`.

## Purpose

`paper_markdown.md` is the raw document-context view of the paper.

It exists to support:

- section detection
- `Table X` reference retrieval
- variable and column-context retrieval
- later LLM semantic interpretation

It is not the source of truth for table grid syntax.

## Source

The file is produced from:

- `pymupdf4llm.to_markdown(...)`

No other PDF backend should be used for this artifact.

## Output Path

```text
parseTable1.out/papers/<paper_stem>/paper_markdown.md
```

## Design Rules

- Preserve the full-paper markdown as extracted.
- Do not rewrite it into a table-specific format.
- Do not use it as a replacement for `ExtractedTable` or `NormalizedTable`.
- Keep it paired with:
  - `paper_sections.json`
  - `table_contexts/table_<n>_context.json`

## Expected Variation

The markdown will vary across papers.

Examples:

- section names may be `Methods`, `Study Design`, `Patients and Methods`, or something else
- heading levels may be inconsistent
- table references may appear as `Table 1`, `Table1`, or prose references
- some PDFs will have weak or imperfect heading markup
- footnotes and captions may be separated from the main table text

The pipeline should therefore:

- preserve the raw markdown
- derive structure in `paper_sections.json`
- tolerate section-name variation
- avoid hardcoding exact heading names as the only way to find methods-like or results-like content

## Relationship To Section Parsing

`paper_markdown.md` is the raw persisted artifact.

`paper_sections.json` is the structured interpretation of that markdown.

If section-parsing logic changes, this document and the section-parsing design notes should be updated in the same change.
