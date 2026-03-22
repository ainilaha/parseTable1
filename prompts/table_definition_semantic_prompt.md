You are interpreting the semantics of a value-free TableDefinition using both table structure and retrieved paper context.
Use only the provided rows, columns, deterministic table definition, and retrieved passages.
Preserve row indices and column indices exactly as supplied.
Do not invent rows, columns, levels, variables, values, or evidence passages.
You may disagree with the deterministic interpretation when the retrieved context supports that disagreement.
Return strict JSON only.
Use evidence_passage_ids whenever you make a semantic claim.
Use unknown when uncertain.

Input payload:
{{TABLE_PAYLOAD_JSON}}

Output schema:
{{OUTPUT_SCHEMA_JSON}}
