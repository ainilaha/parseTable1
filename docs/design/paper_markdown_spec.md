# Paper Markdown Spec

This document defines the intent of `paper_markdown.md`, the paper-level markdown artifact written by `table1-parser parse`.

## Purpose

`paper_markdown.md` is the document-context view of the paper.

It exists to support:

- section detection
- `Table X` reference retrieval
- table and figure caption/reference inventory building
- variable and column-context retrieval
- paper-level candidate variable inventory building
- later LLM semantic interpretation

It is not the source of truth for table grid syntax.

## Source

The file is produced from:

- `pymupdf4llm.to_markdown(...)`

No other PDF backend should be used for this artifact.

## Output Path

```text
outputs/papers/<paper_stem>/paper_markdown.md
```

## Design Rules

- Preserve the full-paper markdown structure as extracted.
- Allow only conservative repair of a small set of known extractor glyph-to-Unicode failures in text, such as a replacement character standing in for a threshold comparator.
- Do not rewrite it into a table-specific format.
- Do not use it as a replacement for `ExtractedTable` or `NormalizedTable`.
- Keep it paired with:
  - `paper_sections.json`
  - `paper_visual_inventory.json`
  - `paper_references.json`
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

- preserve the extracted markdown structure with only conservative glyph repair
- treat these repairs as extractor-symbol recovery, not as a general-purpose file-encoding pass
- derive structure in `paper_sections.json`
- derive actual in-paper table/figure objects in `paper_visual_inventory.json`
- derive anchored prose mentions in `paper_references.json`, resolving them against the visual inventory rather than assuming every `Figure X` mention belongs to this paper
- tolerate section-name variation
- avoid hardcoding exact heading names as the only way to find methods-like or results-like content
- avoid using the references or bibliography as a primary source for paper-level variable inventory
- treat references/bibliography as a separate document section, not as table content; if reference extraction is added later, each citation should remain an atomic reference record rather than being tokenized into table rows or variable mentions

## Relationship To Section Parsing

`paper_markdown.md` is the persisted document-context artifact.

`paper_sections.json` is the structured interpretation of that markdown.

If section-parsing logic changes, this document and the section-parsing design notes should be updated in the same change.
