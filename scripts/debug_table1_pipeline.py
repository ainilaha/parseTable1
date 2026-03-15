from table1_parser.extract.pdfplumber_extractor import PDFPlumberExtractor
from table1_parser.normalize.interpretation_view import build_normalized_table
from table1_parser.heuristics.row_classifier import classify_rows
from table1_parser.heuristics.variable_grouper import group_variables
from table1_parser.heuristics.column_role_detector import detect_column_roles
from table1_parser.heuristics.value_pattern_detector import detect_value_pattern

PDF = "testpapers/cobaltpaper.pdf"

extractor = PDFPlumberExtractor()

tables = extractor.extract(PDF)

print("\nDetected tables:", len(tables))

table = tables[0]

print("\nExtracted table size:", table.n_rows, "rows x", table.n_cols, "cols")

normalized = build_normalized_table(table)

print("\nHeader rows:")
for row in normalized.header_rows:
    print(row)

print("\nBody rows:")
for row in normalized.body_rows[:10]:
    print(row)

print("\nRow signatures:")

for rv in normalized.row_views:
    print(
        rv.row_idx,
        "| raw:", rv.first_cell_raw,
        "| norm:", rv.first_cell_normalized,
        "| alpha:", rv.first_cell_alpha_only,
        "| numeric:", rv.numeric_cell_count,
        "| trailing:", rv.has_trailing_values,
    )

print("\nRow classifications")

row_classes = classify_rows(normalized)

for r in row_classes:
    print(r)

print("\nVariable groups")

groups = group_variables(normalized, row_classes)

for g in groups:
    print(g)

print("\nColumn roles")

roles = detect_column_roles(normalized)

for r in roles:
    print(r)

print("\nValue pattern examples")

for row in normalized.body_rows:
    for cell in row[1:]:
        if cell:
            print(cell, "->", detect_value_pattern(cell))
            break
