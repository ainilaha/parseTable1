Read:

- AGENTS.md
- docs/codex_build_spec.md

Implement one new feature set only.

## Goal

Build a small synthetic document generator for the table-parsing project.

The generator should create:

1. a PDF document containing arbitrary text plus a Table 1-style table
2. a matching truth JSON file describing the intended table structure

The purpose is benchmarking and validation:
- generate controlled test PDFs
- run them back through the parser
- compare parser output to known truth

Do not redesign the existing parser.
Do not add LLM code.
Keep the implementation modular and focused.

---

# Scope

Implement a synthetic document / Table 1 generator with these capabilities:

- read a structured table specification
- render a simple document containing:
  - title
  - optional paragraph text
  - Table 1 caption
  - the table itself
  - optional notes
- export the document to PDF
- export the ground-truth table structure to JSON

The first version does not need to generate realistic epidemiology prose.
It only needs enough surrounding text to create a plausible test document.

---

# High-level design

The generator should take as input a structured spec file such as JSON.

From that spec it should generate:

- `output.pdf`
- `output_truth.json`

Optional intermediate artifacts are acceptable:
- `output.html`
- `output.md`

The PDF should be suitable for passing back through the current parser.

The truth JSON should be suitable for evaluation later.

---

# Recommended rendering approach

Prefer this rendering path:

1. structured spec
2. HTML generation
3. PDF rendering from HTML

Rationale:
- easier layout control than LaTeX for this use case
- easier to vary indentation, rules, captions, spacing
- easier to generate families of test cases

If HTML-to-PDF is difficult in the current repo, a Markdown-to-PDF or reportlab-based fallback is acceptable, but HTML is preferred.

---

# Repository structure

Add code under a new module path such as:

table1_parser/synthetic/
  spec_models.py
  html_renderer.py
  pdf_renderer.py
  truth_writer.py
  generator.py

Add example inputs under:

examples/synthetic_specs/

Add outputs only as small examples if needed. Do not commit large generated artifacts.

---

# Input specification

Use a JSON-driven table spec.

The spec should support at least:

- document title
- optional subtitle
- optional paragraphs
- table caption
- column headers
- row definitions
- optional footnotes
- optional layout settings

Example conceptual structure:

{
  "document_title": "Association of RA status with baseline characteristics",
  "paragraphs": [
    "This is a synthetic epidemiology-style document created for parser testing."
  ],
  "table_caption": "Table 1. Baseline characteristics by RA status",
  "columns": ["Characteristics", "Overall", "Non-RA", "RA", "p-value"],
  "rows": [
    {
      "type": "continuous",
      "label": "Age (yrs)",
      "values": ["53.2 (12.1)", "52.7 (11.9)", "61.0 (13.0)", "<0.001"]
    },
    {
      "type": "continuous",
      "label": "n",
      "values": ["5490", "5171", "319", ""]
    },
    {
      "type": "categorical",
      "label": "Sex",
      "levels": [
        {
          "label": "Male",
          "values": ["2697 (49.1)", "2568 (49.7)", "129 (40.4)", ""]
        },
        {
          "label": "Female",
          "values": ["2793 (50.9)", "2603 (50.3)", "190 (59.6)", "0.002"]
        }
      ]
    }
  ],
  "footnotes": [
    "Values are synthetic and for parser testing only."
  ],
  "layout": {
    "indent_levels": true,
    "horizontal_rules": true
  }
}

---

# Required row types

Support at least these row types:

### 1. continuous
A one-row variable with direct displayed values.

Example:
- `Age (yrs)`
- `BMI, mean ± SD`
- `n`

### 2. categorical
A parent row with one or more level rows.

Example:
- `Sex`
  - `Male`
  - `Female`

### 3. categorical_inline
A one-row categorical summary where the level is included in the row label.

Examples:
- `Gender = Female (%)`
- `Female (%)`

This row type is useful for testing cases where there is no separate parent row.

### 4. section_header
Optional display-only group heading.

Example:
- `Demographic characteristics`

---

# Layout variation support

The generator should support a small number of layout switches so we can test parser robustness.

At minimum support:

### 1. indentation on/off
Whether level rows are visually indented under categorical parent rows.

### 2. horizontal rules on/off
Whether horizontal lines appear above/below the header and optionally elsewhere.

### 3. parent row empty vs parent row with values
Whether categorical parent rows have blank value cells or some summary cells.

### 4. wrapped labels optional
Allow a long label to wrap across lines when desired.

These options should come from the input spec.

Do not overbuild beyond this first set.

---

# Truth JSON

The generator must also emit a truth JSON file describing the intended table structure.

This truth file should include:

- document title
- table caption
- columns
- header rows
- variables
- row types
- variable blocks
- levels
- displayed values
- layout features used

The truth JSON should be explicit enough to evaluate parser output later.

Example fields to include:

- `header_rows`
- `variables`
- `columns`
- `rows`
- `value_records`
- `layout_features`

For each variable, include:
- variable_name
- variable_type
- row_start
- row_end
- levels if any

For each displayed value, include:
- variable_name
- level_label if any
- column_name
- raw_value

---

# Required functions

Implement at least these functions:

### 1. `load_table_spec(path)`
Read and validate the input JSON spec.

### 2. `render_html_document(spec)`
Return an HTML string for the synthetic document.

### 3. `render_pdf_from_html(html, output_path)`
Render the HTML to PDF.

If a PDF backend needs to be abstracted, keep it small.

### 4. `build_truth_json(spec)`
Construct the truth JSON object from the same spec.

### 5. `generate_synthetic_document(spec_path, output_prefix)`
Main orchestration function that produces:
- PDF
- truth JSON
- optionally HTML

---

# CLI / script behavior

Add a small runnable entrypoint or script, for example:

scripts/generate_synthetic_table_doc.py

or a CLI subcommand if that fits the current project style.

It should run like:

python scripts/generate_synthetic_table_doc.py examples/synthetic_specs/basic_table1.json outputs/basic_table1

This should create:
- `outputs/basic_table1.pdf`
- `outputs/basic_table1_truth.json`
- optionally `outputs/basic_table1.html`

Keep the interface simple.

---

# Required example specs

Add at least 3 small example spec files under:

examples/synthetic_specs/

Examples:

### 1. basic_table1.json
- one header row
- one continuous variable
- one categorical variable with 2 levels
- horizontal rules on
- indentation on

### 2. no_indent_table1.json
- categorical levels flush-left
- horizontal rules on
- useful for testing indentation-informative logic

### 3. inline_category_table1.json
- includes rows like `Gender = Female (%)`
- includes `n` row
- useful for tricky row-type testing

Keep examples small.

---

# Tests

Add focused tests for:

1. loading and validating a synthetic spec
2. HTML rendering contains expected title/caption/table text
3. truth JSON contains expected variable blocks and row types
4. layout options such as indentation and horizontal rules affect output
5. generator creates output files successfully for a small example spec

Do not add huge generated artifacts.

---

# Constraints

- keep the implementation small and modular
- do not redesign the parser
- do not add LLM code
- do not hardcode paper-specific logic
- do not add unnecessary dependencies
- do not commit large generated PDFs unless explicitly requested
- preserve a clean separation between:
  - input spec
  - visual rendering
  - truth generation

---

# Deliverable

After this change, the repo should support generating a synthetic PDF plus matching truth JSON from a structured table spec.

This should allow the project to create controlled benchmark documents for parser testing.
