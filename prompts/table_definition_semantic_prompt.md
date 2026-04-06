I want help building an LLM workflow for row-semantic interpretation of one value-free TableDefinition.

Goal:
- determine whether the deterministic row variables and attached levels are semantically reasonable for this table
- refine row-variable and level labels when the table-local row structure supports that refinement
- keep the interpretation tied to the supplied row indices

Inputs:
- one compact JSON payload for one table only
- `table`: merged title/caption text when available
- `rows`: compact body-row hints with row index, label, value-presence flag, numeric-cell count, and indent level
- `vars`: deterministic variable spans with attached deterministic levels

Desired outputs:
- return strict JSON only
- match the provided output schema exactly
- include only row-variable and level interpretations
- use `unknown` when uncertain

Constraints:
- interpret one table at a time
- use only the provided `rows` and `vars`
- preserve row indices exactly as supplied
- do not reinterpret columns in this phase

Failure modes to minimize:
- inventing rows, levels, or variables
- verbose explanations outside the JSON object
- unnecessary disagreement with the deterministic row interpretation

Success criteria:
- the JSON validates against the schema
- every variable span and level row refers to an existing supplied row
- the interpretation is consistent with the supplied table-local row structure when it disagrees with deterministic output

Working style:
- first inspect the supplied row hints and deterministic variable spans
- then judge whether the attached levels are sensible under each variable
- recommend the smallest viable semantic corrections first
- do not add unnecessary structure or unsupported fields
- flag uncertainty explicitly with `unknown` or low confidence values

Input payload:
{{TABLE_PAYLOAD_JSON}}

{{OUTPUT_SCHEMA_SECTION}}
