Read:

- AGENTS.md
- docs/design/codex_build_spec.md

Implement **Phase 5 only**.

## Goal

Add an LLM-assisted interpretation layer that refines the existing heuristic parse of a normalized Table 1.

This phase should use:

- `NormalizedTable`
- heuristic outputs from Phase 4

to produce a structured LLM interpretation of:

- variables
- variable types
- row ranges
- levels
- column roles
- notes

Do not implement full final validation or final end-to-end output yet.

---

## Do not implement

Do NOT add:

- direct PDF parsing by the LLM
- changes to extraction architecture
- major changes to normalization
- final markdown reporting
- full CLI parse pipeline
- external API-specific hardcoding
- broad refactors of previous phases

If a tiny interface change is needed, keep it minimal.

---

## Files to add

Implement only these modules:

- `table1_parser/llm/client.py`
- `table1_parser/llm/prompts.py`
- `table1_parser/llm/parser.py`
- `table1_parser/llm/schemas.py`

You may add one small helper if needed, but keep scope tight.

---

## Functional requirements

### 1. LLM client abstraction

Create a provider-agnostic LLM client abstraction.

Requirements:
- support a structured completion interface
- do not hardcode one provider into the architecture
- an OpenAI-compatible implementation is acceptable, but keep it behind an interface

Suggested method shape:

- `structured_completion(prompt: str, schema: dict) -> dict`

Keep this layer small.

---

### 2. Prompt builder

Implement prompt-building logic that converts:

- `NormalizedTable`
- heuristic row classifications
- heuristic variable groups
- heuristic column roles

into a compact LLM input payload.

The LLM should receive only normalized table information, not raw PDF bytes and not full page text.

The prompt should explicitly instruct:

- preserve row indices exactly
- do not invent rows or columns
- use only the provided rows
- identify variable boundaries
- identify levels under categorical variables
- infer column roles conservatively
- return strict JSON only
- use `unknown` when uncertain

---

### 3. Structured LLM schema

Define the expected LLM output schema for:

- variables
- columns
- notes

Variables should include:
- variable_name
- variable_type
- row_start
- row_end
- levels
- confidence

Columns should include:
- col_idx
- column_name
- inferred_role
- confidence

Levels should include:
- label
- row_idx

This should align closely with the existing project schemas, but can be an intermediate LLM contract if cleaner.

---

### 4. LLM parser

Implement a parser that:

- builds the prompt/input payload
- calls the LLM client abstraction
- parses the structured JSON response
- returns a typed intermediate object

This phase should produce a preliminary semantic interpretation, not final validated output.

The parser should fail safely:
- if the model response is invalid, raise a structured error or return a partial result with notes
- do not silently accept malformed output

---

## Input to the LLM

The LLM input should be compact and structured.

It should include:
- table title
- caption
- header rows
- body rows
- row signatures or row classifications
- heuristic variable block guesses if available
- heuristic column role guesses if available

Example shape:

```json
{
  "table_id": "tbl-llm",
  "title": "Table 1. Baseline characteristics of participants",
  "caption": "Characteristics by diabetes status",
  "header_rows": [
    ["Characteristic", "Overall", "No diabetes", "Diabetes", "P-value"]
  ],
  "body_rows": [
    ["Age, years", "52.3 (14.1)", "49.1 (13.2)", "61.8 (11.3)", "<0.001"],
    ["Sex", "", "", "", ""],
    ["Male", "412 (48.2)", "310 (44.1)", "102 (60.7)", ""],
    ["Female", "443 (51.8)", "393 (55.9)", "50 (39.3)", ""]
  ],
  "heuristics": {
    "row_classifications": [],
    "variable_blocks": [],
    "column_roles": []
  }
}
