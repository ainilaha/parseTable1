"""Ground-truth JSON generation for synthetic documents."""

from __future__ import annotations

from table1_parser.synthetic.spec_models import SyntheticDocumentSpec, expand_display_rows


def build_truth_json(spec: SyntheticDocumentSpec) -> dict[str, object]:
    """Construct the truth representation for a generated synthetic table."""

    display_rows = expand_display_rows(spec)
    variables: list[dict[str, object]] = []
    value_records: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    header_rows = [0]

    categorical_lookup: dict[str, dict[str, object]] = {}
    for row in display_rows:
        row_entry = {
            "body_row_idx": row.body_row_idx,
            "table_row_idx": row.body_row_idx + len(header_rows),
            "row_type": row.row_type,
            "label": row.label,
            "values": row.values,
            "variable_name": row.variable_name,
            "level_label": row.level_label,
            "parent_label": row.parent_label,
            "indent_level": row.indent_level,
        }
        rows.append(row_entry)

        if row.row_type in {"continuous", "categorical_inline"}:
            variables.append(
                {
                    "variable_name": row.variable_name,
                    "variable_label": row.label,
                    "variable_type": "continuous" if row.row_type == "continuous" else "categorical_inline",
                    "row_start": row.body_row_idx,
                    "row_end": row.body_row_idx,
                    "levels": [],
                }
            )
        elif row.row_type == "categorical_parent":
            variable = {
                "variable_name": row.variable_name,
                "variable_label": row.label,
                "variable_type": "categorical",
                "row_start": row.body_row_idx,
                "row_end": row.body_row_idx,
                "levels": [],
            }
            variables.append(variable)
            categorical_lookup[row.variable_name or f"var_{row.body_row_idx}"] = variable
        elif row.row_type == "level" and row.variable_name in categorical_lookup:
            parent = categorical_lookup[row.variable_name]
            parent["row_end"] = row.body_row_idx
            parent["levels"].append({"label": row.level_label, "row_idx": row.body_row_idx})

        for offset, raw_value in enumerate(row.values, start=1):
            value_records.append(
                {
                    "body_row_idx": row.body_row_idx,
                    "table_row_idx": row.body_row_idx + len(header_rows),
                    "col_idx": offset,
                    "column_name": spec.columns[offset],
                    "variable_name": row.variable_name,
                    "level_label": row.level_label,
                    "raw_value": raw_value,
                }
            )

    return {
        "document_title": spec.document_title,
        "table_caption": spec.table_caption,
        "columns": spec.columns,
        "header_rows": header_rows,
        "rows": rows,
        "variables": variables,
        "value_records": value_records,
        "layout_features": spec.layout.model_dump(mode="json"),
    }
