## LLM Integration Rules

The Phase 5 LLM layer must follow these principles.

### Prompt templates must live in the repository

All prompts used by the LLM must be stored as files under:

prompts/

Example:

prompts/table_interpretation_prompt.md

Do not hardcode full prompts inside Python code.

The code may substitute placeholders inside the template, but the template text itself must remain in the repository.

This makes prompts:

- version controlled
- inspectable
- easier to iterate on

---

### Prompt loader behavior

The code must load the prompt template from disk when constructing the LLM request.

A simple prompt loader helper should:

- read the template file from `prompts/`
- substitute placeholders such as `{{TABLE_PAYLOAD_JSON}}`
- return the final prompt string

The loader should remain simple.

Optional improvement:
- cache the prompt in memory within the process so the file is not re-read on every call

Do not add complicated prompt-management systems.

---

### LLM payload must be structured

The LLM must receive a **compact structured payload** describing the table.

The payload must include:

- title
- caption
- header rows
- body rows
- row indices
- heuristic row classifications
- heuristic variable block guesses if available
- heuristic column role guesses if available
- row structural hints when available

Examples of row hints:

- numeric cell count
- whether trailing cells contain values
- indent level if available

Do not send raw PDF text or page content.

---

### Parser architecture rule

The architecture must remain:

PDF
→ extraction
→ normalization
→ heuristic interpretation
→ LLM refinement

The LLM should refine heuristic output, not replace heuristics.

---

### Debugging transparency

When debug mode is enabled, the system should allow inspection of:

- the heuristic interpretation
- the LLM payload
- the LLM response
- the final interpreted structure

---

### Security

LLM providers must be configured using environment variables.

Do not hardcode API keys.

Do not commit secrets.

---

### Testing rules

Tests must mock LLM responses.

Do not rely on live API calls during tests.

Payload generation and prompt rendering should be testable independently.
