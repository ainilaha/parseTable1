#!/usr/bin/env Rscript

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0) y else x
}

read_json_file <- function(json_path) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("The 'jsonlite' package is required. Install it with install.packages('jsonlite').", call. = FALSE)
  }
  if (!file.exists(json_path)) {
    stop(sprintf("JSON file not found: %s", json_path), call. = FALSE)
  }
  json_text <- paste(readLines(json_path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  jsonlite::fromJSON(json_text, simplifyVector = FALSE)
}

read_text_file <- function(path) {
  if (!file.exists(path)) {
    return(NULL)
  }
  paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
}

paper_output_paths <- function(paper_dir) {
  list(
    extracted = file.path(paper_dir, "extracted_tables.json"),
    normalized = file.path(paper_dir, "normalized_tables.json"),
    deterministic = file.path(paper_dir, "table_definitions.json"),
    llm = file.path(paper_dir, "table_definitions_llm.json"),
    paper_markdown = file.path(paper_dir, "paper_markdown.md"),
    paper_sections = file.path(paper_dir, "paper_sections.json"),
    table_context_dir = file.path(paper_dir, "table_contexts")
  )
}

read_optional_json <- function(path) {
  if (!file.exists(path)) {
    return(NULL)
  }
  read_json_file(path)
}

read_table_contexts <- function(context_dir) {
  if (!dir.exists(context_dir)) {
    return(list())
  }
  paths <- sort(list.files(context_dir, pattern = "^table_[0-9]+_context\\.json$", full.names = TRUE))
  contexts <- lapply(paths, read_json_file)
  names(contexts) <- vapply(contexts, function(x) as.character(as.integer(x$table_index %||% -1L)), character(1))
  contexts
}

load_paper_outputs <- function(paper_dir) {
  paths <- paper_output_paths(paper_dir)
  list(
    paper_dir = normalizePath(paper_dir, winslash = "/", mustWork = TRUE),
    extracted_tables = read_json_file(paths$extracted),
    normalized_tables = read_json_file(paths$normalized),
    table_definitions = read_json_file(paths$deterministic),
    table_definitions_llm = read_optional_json(paths$llm),
    paper_markdown = read_text_file(paths$paper_markdown),
    paper_sections = read_json_file(paths$paper_sections),
    table_contexts = read_table_contexts(paths$table_context_dir)
  )
}

table_context_by_index <- function(outputs, table_index = 0L) {
  key <- as.character(as.integer(table_index))
  context <- outputs$table_contexts[[key]]
  if (is.null(context)) {
    stop(sprintf("No table context found for table_index=%s.", key), call. = FALSE)
  }
  context
}

table_definitions_by_index <- function(outputs, table_index = 0L) {
  idx <- as.integer(table_index) + 1L
  deterministic <- outputs$table_definitions[[idx]]
  if (is.null(deterministic)) {
    stop(sprintf("No deterministic table definition found for table_index=%s.", table_index), call. = FALSE)
  }
  llm <- NULL
  if (!is.null(outputs$table_definitions_llm) && length(outputs$table_definitions_llm) >= idx) {
    llm <- outputs$table_definitions_llm[[idx]] %||% NULL
  }
  if (is.null(llm) && !is.null(outputs$table_definitions_llm)) {
    llm_matches <- Filter(
      function(x) identical(as.character(x$table_id %||% ""), as.character(deterministic$table_id %||% "")),
      outputs$table_definitions_llm
    )
    llm <- llm_matches[[1]] %||% NULL
  }
  list(deterministic = deterministic, llm = llm)
}

table_definition_variant_by_index <- function(outputs, table_index = 0L, variant = c("deterministic", "llm")) {
  variant <- match.arg(variant)
  definitions <- table_definitions_by_index(outputs, table_index)
  definition <- definitions[[variant]] %||% NULL
  if (is.null(definition)) {
    stop(
      sprintf("No %s table definition found for table_index=%s.", variant, as.integer(table_index)),
      call. = FALSE
    )
  }
  definition
}

normalize_variable_rows <- function(variables, source) {
  rows <- lapply(variables %||% list(), function(x) {
    data.frame(
      key = sprintf("%s:%s", as.integer(x$row_start %||% -1L), as.integer(x$row_end %||% -1L)),
      row_start = as.integer(x$row_start %||% -1L),
      row_end = as.integer(x$row_end %||% -1L),
      variable_label = as.character(x$variable_label %||% x$variable_name %||% ""),
      variable_type = as.character(x$variable_type %||% ""),
      disagrees_with_deterministic = as.logical(x$disagrees_with_deterministic %||% NA),
      source = source,
      stringsAsFactors = FALSE
    )
  })
  if (length(rows) == 0) {
    return(data.frame(key = character(), row_start = integer(), row_end = integer(), variable_label = character(), variable_type = character(), disagrees_with_deterministic = logical(), source = character(), stringsAsFactors = FALSE))
  }
  do.call(rbind, rows)
}

normalize_level_rows <- function(variables, source) {
  rows <- list()
  for (variable in variables %||% list()) {
    for (level in variable$levels %||% list()) {
      rows[[length(rows) + 1L]] <- data.frame(
        key = as.character(as.integer(level$row_idx %||% -1L)),
        row_idx = as.integer(level$row_idx %||% -1L),
        level_label = as.character(level$level_label %||% level$level_name %||% ""),
        parent_label = as.character(variable$variable_label %||% variable$variable_name %||% ""),
        disagrees_with_deterministic = as.logical(level$disagrees_with_deterministic %||% NA),
        source = source,
        stringsAsFactors = FALSE
      )
    }
  }
  if (length(rows) == 0) {
    return(data.frame(key = character(), row_idx = integer(), level_label = character(), parent_label = character(), disagrees_with_deterministic = logical(), source = character(), stringsAsFactors = FALSE))
  }
  do.call(rbind, rows)
}

normalize_column_rows <- function(columns, source) {
  rows <- lapply(columns %||% list(), function(x) {
    data.frame(
      key = as.character(as.integer(x$col_idx %||% -1L)),
      col_idx = as.integer(x$col_idx %||% -1L),
      column_label = as.character(x$column_label %||% x$column_name %||% ""),
      inferred_role = as.character(x$inferred_role %||% ""),
      grouping_variable_hint = as.character(x$grouping_variable_hint %||% ""),
      disagrees_with_deterministic = as.logical(x$disagrees_with_deterministic %||% NA),
      source = source,
      stringsAsFactors = FALSE
    )
  })
  if (length(rows) == 0) {
    return(data.frame(key = character(), col_idx = integer(), column_label = character(), inferred_role = character(), grouping_variable_hint = character(), disagrees_with_deterministic = logical(), source = character(), stringsAsFactors = FALSE))
  }
  do.call(rbind, rows)
}

compare_rows <- function(left, right, key_col, compare_cols, left_suffix = "deterministic", right_suffix = "llm") {
  merged <- merge(left, right, by = key_col, all = TRUE, suffixes = c(paste0("_", left_suffix), paste0("_", right_suffix)), sort = TRUE)
  status <- character(nrow(merged))
  for (i in seq_len(nrow(merged))) {
    if (is.na(merged[[paste0(compare_cols[[1]], "_", left_suffix)]][i])) {
      status[i] <- paste0(right_suffix, "_only")
    } else if (is.na(merged[[paste0(compare_cols[[1]], "_", right_suffix)]][i])) {
      status[i] <- paste0(left_suffix, "_only")
    } else {
      same <- all(vapply(compare_cols, function(col) {
        identical(
          merged[[paste0(col, "_", left_suffix)]][i] %||% "",
          merged[[paste0(col, "_", right_suffix)]][i] %||% ""
        )
      }, logical(1)))
      status[i] <- if (same) "same" else "different"
    }
  }
  merged$status <- status
  merged
}

print_comparison_block <- function(title, x) {
  cat(title, "\n", sep = "")
  if (nrow(x) == 0) {
    cat("[No rows]\n\n")
    return(invisible(x))
  }
  print(x, row.names = FALSE, right = FALSE)
  cat("\n")
  invisible(x)
}

compare_table_definitions <- function(paper_dir, table_index = 0L) {
  outputs <- load_paper_outputs(paper_dir)
  definitions <- table_definitions_by_index(outputs, table_index)
  if (is.null(definitions$llm)) {
    stop("No table_definitions_llm.json found for this paper.", call. = FALSE)
  }
  compare_table_definition_runs(
    paper_dir_a = paper_dir,
    paper_dir_b = paper_dir,
    table_index = table_index,
    variant_a = "deterministic",
    variant_b = "llm",
    label_a = "deterministic",
    label_b = "llm"
  )
}

compare_table_definition_runs <- function(
  paper_dir_a,
  paper_dir_b,
  table_index = 0L,
  variant_a = c("deterministic", "llm"),
  variant_b = c("deterministic", "llm"),
  label_a = NULL,
  label_b = NULL
) {
  variant_a <- match.arg(variant_a)
  variant_b <- match.arg(variant_b)

  outputs_a <- load_paper_outputs(paper_dir_a)
  outputs_b <- load_paper_outputs(paper_dir_b)
  definition_a <- table_definition_variant_by_index(outputs_a, table_index = table_index, variant = variant_a)
  definition_b <- table_definition_variant_by_index(outputs_b, table_index = table_index, variant = variant_b)

  label_a <- label_a %||% sprintf("run_a_%s", variant_a)
  label_b <- label_b %||% sprintf("run_b_%s", variant_b)

  variables <- compare_rows(
    normalize_variable_rows(definition_a$variables, label_a),
    normalize_variable_rows(definition_b$variables, label_b),
    "key",
    c("variable_label", "variable_type"),
    left_suffix = "left",
    right_suffix = "right"
  )
  levels <- compare_rows(
    normalize_level_rows(definition_a$variables, label_a),
    normalize_level_rows(definition_b$variables, label_b),
    "key",
    c("level_label", "parent_label"),
    left_suffix = "left",
    right_suffix = "right"
  )
  columns <- compare_rows(
    normalize_column_rows(definition_a$column_definition$columns, label_a),
    normalize_column_rows(definition_b$column_definition$columns, label_b),
    "key",
    c("column_label", "inferred_role", "grouping_variable_hint"),
    left_suffix = "left",
    right_suffix = "right"
  )

  cat(sprintf("Table comparison for table_index=%s\n", as.integer(table_index)))
  cat(sprintf("Left: %s (%s)\n", label_a, variant_a))
  cat(sprintf("Right: %s (%s)\n\n", label_b, variant_b))

  print_comparison_block("Variables", variables)
  print_comparison_block("Levels", levels)
  print_comparison_block("Columns", columns)

  invisible(
    list(
      variables = variables,
      levels = levels,
      columns = columns,
      metadata = list(
        paper_dir_a = normalizePath(paper_dir_a, winslash = "/", mustWork = TRUE),
        paper_dir_b = normalizePath(paper_dir_b, winslash = "/", mustWork = TRUE),
        table_index = as.integer(table_index),
        variant_a = variant_a,
        variant_b = variant_b,
        label_a = label_a,
        label_b = label_b
      )
    )
  )
}

show_table_context <- function(paper_dir, table_index = 0L, match_type = NULL) {
  outputs <- load_paper_outputs(paper_dir)
  context <- table_context_by_index(outputs, table_index)
  passages <- context$passages %||% list()
  if (!is.null(match_type)) {
    passages <- Filter(function(x) identical(x$match_type %||% "", match_type), passages)
  }

  cat(sprintf("Table context for table_index=%s\n", as.integer(table_index)))
  if (!is.null(context$table_label)) {
    cat(sprintf("Label: %s\n", context$table_label))
  }
  if (!is.null(context$title) && nzchar(context$title)) {
    cat(sprintf("Title: %s\n", context$title))
  }
  if (!is.null(context$caption) && nzchar(context$caption)) {
    cat(sprintf("Caption: %s\n", context$caption))
  }
  cat("\n")

  for (passage in passages) {
    cat(sprintf("[%s] %s | %s | score=%s\n", passage$passage_id, passage$heading %||% "", passage$match_type %||% "", format(passage$score %||% NA)))
    cat(passage$text %||% "", "\n\n", sep = "")
  }

  invisible(passages)
}

resolve_evidence_passages <- function(table_context, passage_ids) {
  passages <- table_context$passages %||% list()
  passage_map <- setNames(passages, vapply(passages, function(x) x$passage_id %||% "", character(1)))
  lapply(passage_ids %||% character(), function(id) passage_map[[id]] %||% NULL)
}

show_llm_evidence <- function(paper_dir, table_index = 0L) {
  outputs <- load_paper_outputs(paper_dir)
  definitions <- table_definitions_by_index(outputs, table_index)
  if (is.null(definitions$llm)) {
    stop("No table_definitions_llm.json found for this paper.", call. = FALSE)
  }
  context <- table_context_by_index(outputs, table_index)
  llm <- definitions$llm

  cat(sprintf("LLM evidence for table_index=%s\n\n", as.integer(table_index)))

  for (variable in llm$variables %||% list()) {
    ids <- variable$evidence_passage_ids %||% list()
    if (length(ids) == 0) {
      next
    }
    cat(sprintf("Variable: %s [%s-%s]\n", variable$variable_label %||% variable$variable_name %||% "", variable$row_start %||% "", variable$row_end %||% ""))
    cat(sprintf("disagrees_with_deterministic: %s\n", as.character(variable$disagrees_with_deterministic %||% FALSE)))
    for (passage in resolve_evidence_passages(context, ids)) {
      if (is.null(passage)) {
        next
      }
      cat(sprintf("  [%s] %s\n", passage$passage_id, passage$heading %||% ""))
      cat(sprintf("  %s\n", passage$text %||% ""))
    }
    cat("\n")
  }

  for (column in llm$column_definition$columns %||% list()) {
    ids <- column$evidence_passage_ids %||% list()
    if (length(ids) == 0) {
      next
    }
    cat(sprintf("Column: %s [col_idx=%s]\n", column$column_label %||% column$column_name %||% "", column$col_idx %||% ""))
    cat(sprintf("disagrees_with_deterministic: %s\n", as.character(column$disagrees_with_deterministic %||% FALSE)))
    for (passage in resolve_evidence_passages(context, ids)) {
      if (is.null(passage)) {
        next
      }
      cat(sprintf("  [%s] %s\n", passage$passage_id, passage$heading %||% ""))
      cat(sprintf("  %s\n", passage$text %||% ""))
    }
    cat("\n")
  }

  invisible(llm)
}
