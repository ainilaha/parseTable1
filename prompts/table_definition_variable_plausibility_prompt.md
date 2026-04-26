You are reviewing an epidemiology paper where Table 1 describes the demographics, baseline characteristics, exposures, covariates, and related descriptive characteristics of the study population.

Your job is to review the semantic plausibility of row-variable definitions for one value-free TableDefinition.

Goal:
- judge whether the inferred `variable_type` fits the variable label and attached levels
- judge whether the attached levels are sensible for categorical variables
- pay special attention to categorical levels and whether they are sensible members, bins, strata, or binary states for the named epidemiologic variable

Domain expectations:
- these variables usually come from epidemiology or clinical descriptive tables, for example age, sex, race/ethnicity, smoking, BMI, comorbidity history, medication use, socioeconomic measures, lab values, disease status, enrollment strata, and exposure categories
- a variable can still be plausible even if it is uncommon, study-specific, or clinically specialized
- threshold-defined bins and cutpoints such as `20-60 years`, `>60 years`, `<1`, `1-1.99`, or `>=30` are common and semantically plausible in epidemiology tables
- judge semantic fit, not whether the study design or prevalence seems typical

Scoring rubric:
- `1.0`: very plausible; label, type, and attached levels fit strongly
- `0.75`: mostly plausible; minor ambiguity only
- `0.5`: ambiguous; could be right but there is meaningful uncertainty
- `0.25`: probably implausible; type or levels do not fit the label well
- `0.0`: clearly implausible or internally inconsistent

Type-specific guidance:
- `continuous`: usually a measurement, quantity, score, duration, age, lab value, or index; it must be a single-row variable and must not have child levels
- `categorical`: label denotes a grouping concept and the child levels are coherent members, bins, or strata of that concept; a categorical variable must have one or more child levels
- `binary`: should be a one-row indicator variable with no child levels; it still implies two states semantically even when the opposite state is not printed as its own row
- one-row labels like `Gender = Female`, `age.cat = >60 years`, `BMI_cat >=30`, or similar threshold-coded indicator names are often plausible binary variables rather than categorical parents
- generic group labels like `Education`, `Smoking`, `Race/ethnicity`, or `Activity level` are usually implausible as standalone no-child variables unless the label itself names one specific indicator state
- `unknown`: use only when the supplied label/type pairing is too ambiguous to evaluate confidently

Secondary evidence:
- `units_hint` and `summary_style_hint` are helpful but not ground truth
- for example, `mean_sd` often supports `continuous`, while `count_pct` or `n_only` often support `categorical` or `binary` count rows

Inputs:
- one compact JSON payload for one table only
- `table`: merged title/caption text when available
- `vars`: supplied variables with row span, printed label, normalized name, inferred type, attached level labels, units hint, and summary-style hint

Desired outputs:
- return strict JSON only
- match the provided output schema exactly
- return the same variables in the same order
- preserve the supplied identity fields and attached levels exactly
- add one `plausibility_score` between `0` and `1` for each variable
- add a short `plausibility_note` only when it helps explain a low or non-obvious score

Constraints:
- use only the supplied `table` and `vars`
- do not invent, remove, split, merge, or rename variables
- do not invent, remove, reorder, or rename levels
- do not judge whether the study result itself is realistic; judge only semantic fit of label, type, and levels
- score variables down when the structure and type are inconsistent, especially if a continuous variable has children, a categorical variable has no children, or a binary variable has children
- if context is limited, prefer a mid-range score instead of an extreme score

Failure modes to minimize:
- copying the wrong variable identity fields
- treating disease rarity, prevalence, or study-specific expectations as implausibility
- over-penalizing variables just because wider paper context is missing
- giving nearly identical default scores to every variable

Success criteria:
- each input variable has one output entry
- `plausibility_score` reflects semantic fit of label, inferred type, and level set
- lower scores correspond to clear type mismatches, incoherent levels, or invalid type/child structure combinations
- the JSON validates exactly

Input payload:
{{TABLE_PAYLOAD_JSON}}

{{OUTPUT_SCHEMA_SECTION}}
