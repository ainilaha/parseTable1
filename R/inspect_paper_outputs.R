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
    parsed = file.path(paper_dir, "parsed_tables.json"),
    processing_status = file.path(paper_dir, "table_processing_status.json"),
    variable_plausibility = file.path(paper_dir, "table_variable_plausibility_llm.json"),
    variable_plausibility_debug_dir = file.path(paper_dir, "llm_variable_plausibility_debug"),
    paper_markdown = file.path(paper_dir, "paper_markdown.md"),
    paper_sections = file.path(paper_dir, "paper_sections.json"),
    paper_variable_inventory = file.path(paper_dir, "paper_variable_inventory.json"),
    table_profiles = file.path(paper_dir, "table_profiles.json"),
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
    parsed_tables = read_optional_json(paths$parsed),
    table_processing_status = read_optional_json(paths$processing_status),
    table_profiles = read_optional_json(paths$table_profiles),
    table_variable_plausibility_llm = read_optional_json(paths$variable_plausibility),
    paper_markdown = read_text_file(paths$paper_markdown),
    paper_sections = read_json_file(paths$paper_sections),
    paper_variable_inventory = read_optional_json(paths$paper_variable_inventory),
    table_contexts = read_table_contexts(paths$table_context_dir)
  )
}

paper_variable_mentions_df <- function(outputs, role_hint = NULL, source_type = NULL, mention_role = NULL) {
  mentions <- outputs$paper_variable_inventory$mentions %||% list()
  rows <- lapply(mentions, function(x) {
    data.frame(
      mention_id = as.character(x$mention_id %||% ""),
      raw_label = as.character(x$raw_label %||% ""),
      normalized_label = as.character(x$normalized_label %||% ""),
      source_type = as.character(x$source_type %||% ""),
      mention_role = as.character(x$mention_role %||% ""),
      canonical_label = as.character(x$canonical_label %||% ""),
      section_id = as.character(x$section_id %||% ""),
      heading = as.character(x$heading %||% ""),
      role_hint = as.character(x$role_hint %||% ""),
      paragraph_index = as.integer(x$paragraph_index %||% NA_integer_),
      evidence_text = as.character(x$evidence_text %||% ""),
      table_id = as.character(x$table_id %||% ""),
      table_index = as.integer(x$table_index %||% NA_integer_),
      table_label = as.character(x$table_label %||% ""),
      priority_weight = as.numeric(x$priority_weight %||% NA_real_),
      confidence = as.numeric(x$confidence %||% NA_real_),
      stringsAsFactors = FALSE
    )
  })
  mentions_df <- if (length(rows) == 0) {
    data.frame(
      mention_id = character(),
      raw_label = character(),
      normalized_label = character(),
      source_type = character(),
      mention_role = character(),
      canonical_label = character(),
      section_id = character(),
      heading = character(),
      role_hint = character(),
      paragraph_index = integer(),
      evidence_text = character(),
      table_id = character(),
      table_index = integer(),
      table_label = character(),
      priority_weight = numeric(),
      confidence = numeric(),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, rows)
  }
  if (!is.null(role_hint)) {
    mentions_df <- mentions_df[mentions_df$role_hint %in% as.character(role_hint), , drop = FALSE]
  }
  if (!is.null(source_type)) {
    mentions_df <- mentions_df[mentions_df$source_type %in% as.character(source_type), , drop = FALSE]
  }
  if (!is.null(mention_role)) {
    mentions_df <- mentions_df[mentions_df$mention_role %in% as.character(mention_role), , drop = FALSE]
  }
  mentions_df
}

paper_variable_candidates_df <- function(outputs, min_priority = NULL) {
  candidates <- outputs$paper_variable_inventory$candidates %||% list()
  rows <- lapply(candidates, function(x) {
    data.frame(
      candidate_id = as.character(x$candidate_id %||% ""),
      preferred_label = as.character(x$preferred_label %||% ""),
      canonical_label = as.character(x$canonical_label %||% ""),
      normalized_label = as.character(x$normalized_label %||% ""),
      canonical_label_source = as.character(x$canonical_label_source %||% ""),
      promotion_basis = as.character(x$promotion_basis %||% ""),
      alternate_labels = paste(unlist(x$alternate_labels %||% list(), use.names = FALSE), collapse = " | "),
      source_types = paste(unlist(x$source_types %||% list(), use.names = FALSE), collapse = " | "),
      section_ids = paste(unlist(x$section_ids %||% list(), use.names = FALSE), collapse = " | "),
      section_role_hints = paste(unlist(x$section_role_hints %||% list(), use.names = FALSE), collapse = " | "),
      table_ids = paste(unlist(x$table_ids %||% list(), use.names = FALSE), collapse = " | "),
      table_indices = paste(unlist(x$table_indices %||% list(), use.names = FALSE), collapse = " | "),
      text_support_count = as.integer(x$text_support_count %||% 0L),
      table_support_count = as.integer(x$table_support_count %||% 0L),
      caption_support_count = as.integer(x$caption_support_count %||% 0L),
      filtered_mention_count = as.integer(x$filtered_mention_count %||% 0L),
      priority_score = as.numeric(x$priority_score %||% NA_real_),
      confidence = as.numeric(x$confidence %||% NA_real_),
      interpretation_status = as.character(x$interpretation_status %||% ""),
      stringsAsFactors = FALSE
    )
  })
  candidates_df <- if (length(rows) == 0) {
    data.frame(
      candidate_id = character(),
      preferred_label = character(),
      canonical_label = character(),
      normalized_label = character(),
      canonical_label_source = character(),
      promotion_basis = character(),
      alternate_labels = character(),
      source_types = character(),
      section_ids = character(),
      section_role_hints = character(),
      table_ids = character(),
      table_indices = character(),
      text_support_count = integer(),
      table_support_count = integer(),
      caption_support_count = integer(),
      filtered_mention_count = integer(),
      priority_score = numeric(),
      confidence = numeric(),
      interpretation_status = character(),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, rows)
  }
  if (!is.null(min_priority)) {
    candidates_df <- candidates_df[candidates_df$priority_score >= as.numeric(min_priority), , drop = FALSE]
  }
  candidates_df
}

show_paper_variable_mentions <- function(paper_dir, role_hint = NULL, source_type = NULL, mention_role = NULL) {
  outputs <- load_paper_outputs(paper_dir)
  mentions_df <- paper_variable_mentions_df(
    outputs,
    role_hint = role_hint,
    source_type = source_type,
    mention_role = mention_role
  )

  cat(sprintf("Paper variable mentions for %s\n\n", normalizePath(paper_dir, winslash = "/", mustWork = TRUE)))
  if (nrow(mentions_df) == 0) {
    cat("[No rows]\n")
    return(invisible(mentions_df))
  }
  print(mentions_df, row.names = FALSE, right = FALSE)
  invisible(mentions_df)
}

show_paper_variable_candidates <- function(paper_dir, min_priority = NULL) {
  outputs <- load_paper_outputs(paper_dir)
  candidates_df <- paper_variable_candidates_df(outputs, min_priority = min_priority)

  cat(sprintf("Paper variable candidates for %s\n\n", normalizePath(paper_dir, winslash = "/", mustWork = TRUE)))
  if (nrow(candidates_df) == 0) {
    cat("[No rows]\n")
    return(invisible(candidates_df))
  }
  print(candidates_df, row.names = FALSE, right = FALSE)
  invisible(candidates_df)
}

normalized_table_by_index <- function(outputs, table_index = 0L) {
  idx <- as.integer(table_index) + 1L
  table <- outputs$normalized_tables[[idx]]
  if (is.null(table)) {
    stop(sprintf("No normalized table found for table_index=%s.", table_index), call. = FALSE)
  }
  table
}

parsed_table_by_index <- function(outputs, table_index = 0L) {
  idx <- as.integer(table_index) + 1L
  table <- (outputs$parsed_tables %||% list())[[idx]]
  if (is.null(table)) {
    stop(sprintf("No parsed table found for table_index=%s.", table_index), call. = FALSE)
  }
  table
}

table_definition_by_index <- function(outputs, table_index = 0L) {
  idx <- as.integer(table_index) + 1L
  table <- outputs$table_definitions[[idx]]
  if (is.null(table)) {
    stop(sprintf("No deterministic table definition found for table_index=%s.", table_index), call. = FALSE)
  }
  table
}

list_llm_variable_plausibility_debug_runs <- function(paper_dir) {
  debug_root <- paper_output_paths(paper_dir)$variable_plausibility_debug_dir
  if (!dir.exists(debug_root)) {
    return(character())
  }
  run_dirs <- sort(list.dirs(debug_root, full.names = TRUE, recursive = FALSE))
  run_dirs[file.exists(file.path(run_dirs, "llm_variable_plausibility_monitoring.json"))]
}

read_llm_variable_plausibility_monitoring <- function(paper_dir, run_id = NULL) {
  run_dirs <- list_llm_variable_plausibility_debug_runs(paper_dir)
  if (length(run_dirs) == 0) {
    stop("No llm_variable_plausibility_debug runs found for this paper.", call. = FALSE)
  }
  selected_dir <- if (is.null(run_id)) {
    run_dirs[[length(run_dirs)]]
  } else {
    candidates <- run_dirs[basename(run_dirs) == run_id]
    if (length(candidates) == 0) {
      stop(sprintf("No llm_variable_plausibility_debug run found for run_id=%s.", run_id), call. = FALSE)
    }
    candidates[[1]]
  }
  payload <- read_json_file(file.path(selected_dir, "llm_variable_plausibility_monitoring.json"))
  list(run_dir = selected_dir, monitoring = payload)
}

table_context_by_index <- function(outputs, table_index = 0L) {
  key <- as.character(as.integer(table_index))
  context <- outputs$table_contexts[[key]]
  if (is.null(context)) {
    stop(sprintf("No table context found for table_index=%s.", key), call. = FALSE)
  }
  context
}

table_processing_status_by_index <- function(outputs, table_index = 0L, table_id = NULL) {
  statuses <- outputs$table_processing_status %||% list()
  if (length(statuses) == 0) {
    return(NULL)
  }

  resolved_table_id <- as.character(table_id %||% "")
  if (!nzchar(resolved_table_id)) {
    idx <- as.integer(table_index) + 1L
    deterministic <- (outputs$table_definitions %||% list())[[idx]] %||% NULL
    normalized <- (outputs$normalized_tables %||% list())[[idx]] %||% NULL
    parsed <- (outputs$parsed_tables %||% list())[[idx]] %||% NULL
    resolved_table_id <- as.character(
      deterministic$table_id %||%
      normalized$table_id %||%
      parsed$table_id %||%
      ""
    )
  }

  if (nzchar(resolved_table_id)) {
    matching_statuses <- Filter(
      function(x) identical(as.character(x$table_id %||% ""), resolved_table_id),
      statuses
    )
    if (length(matching_statuses) > 0) {
      return(matching_statuses[[1]])
    }
  }

  idx <- as.integer(table_index) + 1L
  if (length(statuses) >= idx) {
    return(statuses[[idx]] %||% NULL)
  }
  NULL
}

table_profile_by_index <- function(outputs, table_index = 0L, table_id = NULL) {
  profiles <- outputs$table_profiles %||% list()
  if (length(profiles) == 0) {
    return(NULL)
  }

  resolved_table_id <- as.character(table_id %||% "")
  if (nzchar(resolved_table_id)) {
    matching_profiles <- Filter(
      function(x) identical(as.character(x$table_id %||% ""), resolved_table_id),
      profiles
    )
    if (length(matching_profiles) > 0) {
      return(matching_profiles[[1]])
    }
  }

  idx <- as.integer(table_index) + 1L
  if (length(profiles) >= idx) {
    return(profiles[[idx]] %||% NULL)
  }
  NULL
}

summarize_table_processing <- function(paper_dir) {
  outputs <- load_paper_outputs(paper_dir)
  table_count <- max(
    length(outputs$extracted_tables %||% list()),
    length(outputs$normalized_tables %||% list()),
    length(outputs$table_definitions %||% list()),
    length(outputs$parsed_tables %||% list())
  )

  rows <- lapply(seq_len(table_count), function(index) {
    table_index <- index - 1L
    extracted <- outputs$extracted_tables[[index]] %||% NULL
    normalized <- outputs$normalized_tables[[index]] %||% NULL
    definition <- outputs$table_definitions[[index]] %||% NULL
    parsed <- outputs$parsed_tables[[index]] %||% NULL
    table_id <- as.character(
      definition$table_id %||%
      normalized$table_id %||%
      parsed$table_id %||%
      extracted$table_id %||%
      ""
    )
    status_record <- table_processing_status_by_index(outputs, table_index = table_index, table_id = table_id)
    table_profile <- table_profile_by_index(outputs, table_index = table_index, table_id = table_id)
    columns <- definition$column_definition$columns %||% definition$columns %||% list()
    attempts <- status_record$attempts %||% list()
    data.frame(
      table_index = as.integer(table_index),
      table_id = table_id,
      title = as.character(
        definition$title %||%
        normalized$title %||%
        parsed$title %||%
        extracted$title %||%
        ""
      ),
      status = as.character(status_record$status %||% NA_character_),
      failure_stage = as.character(status_record$failure_stage %||% NA_character_),
      failure_reason = as.character(status_record$failure_reason %||% NA_character_),
      attempt_count = as.integer(length(attempts)),
      successful_attempt_count = as.integer(
        sum(vapply(attempts, function(attempt) isTRUE(attempt$succeeded %||% FALSE), logical(1)))
      ),
      variable_count = as.integer(length(definition$variables %||% list())),
      usable_column_count = as.integer(
        sum(vapply(
          columns,
          function(column) !identical(as.character(column$inferred_role %||% "unknown"), "unknown"),
          logical(1)
        ))
      ),
      value_count = as.integer(length(parsed$values %||% list())),
      table_family = as.character(table_profile$table_family %||% NA_character_),
      grid_refinement_source = as.character(extracted$metadata$grid_refinement_source %||% NA_character_),
      stringsAsFactors = FALSE
    )
  })

  summary_df <- if (length(rows) == 0) {
    data.frame(
      table_index = integer(),
      table_id = character(),
      title = character(),
      status = character(),
      failure_stage = character(),
      failure_reason = character(),
      attempt_count = integer(),
      successful_attempt_count = integer(),
      variable_count = integer(),
      usable_column_count = integer(),
      value_count = integer(),
      table_family = character(),
      grid_refinement_source = character(),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, rows)
  }

  cat(sprintf("Table processing summary for %s\n\n", outputs$paper_dir))
  if (nrow(summary_df) == 0) {
    cat("[No rows]\n")
    return(invisible(summary_df))
  }
  print(summary_df, row.names = FALSE, right = FALSE)
  invisible(summary_df)
}

show_table_processing <- function(paper_dir, table_index = 0L) {
  outputs <- load_paper_outputs(paper_dir)
  normalized <- normalized_table_by_index(outputs, table_index)
  definition <- table_definition_by_index(outputs, table_index)
  parsed <- parsed_table_by_index(outputs, table_index)
  status_record <- table_processing_status_by_index(
    outputs,
    table_index = table_index,
    table_id = as.character(definition$table_id %||% normalized$table_id %||% parsed$table_id %||% "")
  )

  cat(sprintf("Table processing for table_index=%s\n", as.integer(table_index)))
  cat(sprintf("table_id: %s\n", definition$table_id %||% normalized$table_id %||% parsed$table_id %||% ""))
  if (!is.null(definition$title) && nzchar(definition$title)) {
    cat(sprintf("title: %s\n", definition$title))
  }
  if (!is.null(definition$caption) && nzchar(definition$caption) && !identical(definition$caption, definition$title)) {
    cat(sprintf("caption: %s\n", definition$caption))
  }

  if (is.null(status_record)) {
    cat("\n[No table_processing_status record found]\n")
    return(invisible(NULL))
  }

  columns <- definition$column_definition$columns %||% definition$columns %||% list()
  usable_column_count <- sum(vapply(
    columns,
    function(column) !identical(as.character(column$inferred_role %||% "unknown"), "unknown"),
    logical(1)
  ))
  cat(sprintf("status: %s\n", status_record$status %||% ""))
  if (!is.null(status_record$failure_stage) && nzchar(status_record$failure_stage)) {
    cat(sprintf("failure_stage: %s\n", status_record$failure_stage))
  }
  if (!is.null(status_record$failure_reason) && nzchar(status_record$failure_reason)) {
    cat(sprintf("failure_reason: %s\n", status_record$failure_reason))
  }
  notes <- as.character(unlist(status_record$notes %||% list(), use.names = FALSE))
  if (length(notes) > 0) {
    cat(sprintf("notes: %s\n", paste(notes, collapse = " | ")))
  }
  cat(sprintf("variable_count: %d\n", length(definition$variables %||% list())))
  cat(sprintf("usable_column_count: %d\n", usable_column_count))
  cat(sprintf("value_count: %d\n\n", length(parsed$values %||% list())))

  attempts <- status_record$attempts %||% list()
  cat("Attempts\n")
  if (length(attempts) == 0) {
    cat("[No rows]\n")
    return(invisible(status_record))
  }
  attempts_df <- do.call(
    rbind,
    lapply(attempts, function(attempt) {
      data.frame(
        stage = as.character(attempt$stage %||% ""),
        name = as.character(attempt$name %||% ""),
        considered = as.logical(attempt$considered %||% FALSE),
        ran = as.logical(attempt$ran %||% FALSE),
        succeeded = as.logical(attempt$succeeded %||% FALSE),
        note = as.character(attempt$note %||% ""),
        stringsAsFactors = FALSE
      )
    })
  )
  print(attempts_df, row.names = FALSE, right = FALSE)
  invisible(status_record)
}

show_table_structure <- function(paper_dir, table_index = 0L, max_rows = NULL) {
  outputs <- load_paper_outputs(paper_dir)
  normalized <- normalized_table_by_index(outputs, table_index)
  definition <- table_definition_by_index(outputs, table_index)
  status_record <- table_processing_status_by_index(
    outputs,
    table_index = table_index,
    table_id = as.character(definition$table_id %||% normalized$table_id %||% "")
  )

  cleaned_rows <- normalized$metadata$cleaned_rows %||% list()
  if (!is.null(max_rows)) {
    max_rows <- as.integer(max_rows)
    cleaned_rows <- cleaned_rows[seq_len(min(length(cleaned_rows), max_rows))]
  }

  cat(sprintf("table_index: %s\n", as.integer(table_index)))
  cat(sprintf("table_id: %s\n", definition$table_id %||% normalized$table_id %||% ""))
  if (!is.null(definition$title) && nzchar(definition$title)) {
    cat(sprintf("title: %s\n", definition$title))
  }
  if (!is.null(definition$caption) && nzchar(definition$caption) && !identical(definition$caption, definition$title)) {
    cat(sprintf("caption: %s\n", definition$caption))
  }
  cat("\n")
  if (!is.null(status_record)) {
    cat(sprintf("processing status: %s\n", status_record$status %||% ""))
    if (!is.null(status_record$failure_stage) && nzchar(status_record$failure_stage)) {
      cat(sprintf("failure_stage: %s\n", status_record$failure_stage))
    }
    if (!is.null(status_record$failure_reason) && nzchar(status_record$failure_reason)) {
      cat(sprintf("failure_reason: %s\n", status_record$failure_reason))
    }
    cat("\n")
  }

  cat("Rows\n")
  if (length(cleaned_rows) == 0) {
    cat("[No cleaned rows]\n\n")
  } else {
    for (i in seq_along(cleaned_rows)) {
      cat(sprintf("%2d | %s\n", i - 1L, paste(unlist(cleaned_rows[[i]], use.names = FALSE), collapse = " | ")))
    }
    cat("\n")
  }

  cat("Columns\n")
  columns <- definition$column_definition$columns %||% definition$columns %||% list()
  if (length(columns) == 0) {
    cat("[No column definitions]\n\n")
  } else {
    for (column in columns) {
      col_idx <- as.integer(column$col_idx %||% -1L)
      label <- as.character(column$column_label %||% column$column_name %||% "")
      role <- as.character(column$inferred_role %||% "")
      group_level <- as.character(column$group_level_label %||% "")
      stat <- as.character(column$statistic_subtype %||% "")
      extras <- Filter(nzchar, c(
        if (nzchar(group_level)) paste0("group_level=", group_level) else "",
        if (nzchar(stat)) paste0("stat=", stat) else ""
      ))
      suffix <- if (length(extras)) paste0(" [", paste(extras, collapse = ", "), "]") else ""
      cat(sprintf("%2d | %s | %s%s\n", col_idx, role, label, suffix))
    }
    cat("\n")
  }

  cat("Variables\n")
  variables <- definition$variables %||% list()
  if (length(variables) == 0) {
    cat("[No variables]\n")
  } else {
    for (variable in variables) {
      label <- as.character(variable$variable_label %||% variable$variable_name %||% "")
      vtype <- as.character(variable$variable_type %||% "")
      row_start <- as.integer(variable$row_start %||% -1L)
      row_end <- as.integer(variable$row_end %||% -1L)
      summary_style <- as.character(variable$summary_style_hint %||% "")
      units <- as.character(variable$units_hint %||% "")
      extras <- Filter(nzchar, c(
        if (nzchar(summary_style)) paste0("summary=", summary_style) else "",
        if (nzchar(units)) paste0("units=", units) else ""
      ))
      suffix <- if (length(extras)) paste0(" [", paste(extras, collapse = ", "), "]") else ""
      cat(sprintf("%2d-%2d | %s | %s%s\n", row_start, row_end, vtype, label, suffix))
      levels <- variable$levels %||% list()
      if (length(levels)) {
        for (level in levels) {
          cat(sprintf(
            "      level row %2d | %s\n",
            as.integer(level$row_idx %||% -1L),
            as.character(level$level_label %||% level$level_name %||% "")
          ))
        }
      }
    }
  }

  invisible(list(
    normalized_table = normalized,
    table_definition = definition
  ))
}

llm_variable_plausibility_review_by_index <- function(outputs, table_index = 0L) {
  reviews <- outputs$table_variable_plausibility_llm %||% list()
  if (length(reviews) == 0) {
    stop("No table_variable_plausibility_llm.json found for this paper.", call. = FALSE)
  }
  idx <- as.integer(table_index) + 1L
  review <- reviews[[idx]] %||% NULL
  if (!is.null(review)) {
    return(review)
  }
  definition <- table_definition_by_index(outputs, table_index)
  review_matches <- Filter(
    function(x) identical(as.character(x$table_id %||% ""), as.character(definition$table_id %||% "")),
    reviews
  )
  if (length(review_matches) == 0) {
    stop(sprintf("No variable-plausibility review found for table_index=%s.", table_index), call. = FALSE)
  }
  review_matches[[1]]
}

llm_variable_plausibility_df <- function(outputs, table_index = NULL) {
  reviews <- outputs$table_variable_plausibility_llm %||% list()
  if (!is.null(table_index)) {
    reviews <- list(llm_variable_plausibility_review_by_index(outputs, table_index = table_index))
  }

  rows <- list()
  for (review in reviews) {
    review_table_id <- as.character(review$table_id %||% "")
    matching_indices <- which(vapply(
      outputs$table_definitions %||% list(),
      function(x) identical(as.character(x$table_id %||% ""), review_table_id),
      logical(1)
    ))
    table_index_value <- if (length(matching_indices) == 0) NA_integer_ else as.integer(matching_indices[[1]] - 1L)
    for (variable in review$variables %||% list()) {
      levels <- variable$levels %||% list()
      rows[[length(rows) + 1L]] <- data.frame(
        table_index = table_index_value,
        table_id = review_table_id,
        row_start = as.integer(variable$row_start %||% NA_integer_),
        row_end = as.integer(variable$row_end %||% NA_integer_),
        variable_name = as.character(variable$variable_name %||% ""),
        variable_label = as.character(variable$variable_label %||% ""),
        variable_type = as.character(variable$variable_type %||% ""),
        levels = paste(
          vapply(levels, function(level) as.character(level$level_label %||% level$level_name %||% ""), character(1)),
          collapse = " | "
        ),
        level_count = as.integer(length(levels)),
        plausibility_score = as.numeric(variable$plausibility_score %||% NA_real_),
        plausibility_note = as.character(variable$plausibility_note %||% ""),
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(rows) == 0) {
    return(data.frame(
      table_index = integer(),
      table_id = character(),
      row_start = integer(),
      row_end = integer(),
      variable_name = character(),
      variable_label = character(),
      variable_type = character(),
      levels = character(),
      level_count = integer(),
      plausibility_score = numeric(),
      plausibility_note = character(),
      stringsAsFactors = FALSE
    ))
  }
  do.call(rbind, rows)
}

show_variable_plausibility_review <- function(review, normalized_table, table_definition) {
  cleaned_rows <- normalized_table$metadata$cleaned_rows %||% list()

  cat(sprintf("Variable plausibility review for table_id=%s\n", review$table_id %||% table_definition$table_id %||% ""))
  if (!is.null(table_definition$title) && nzchar(table_definition$title)) {
    cat(sprintf("title: %s\n", table_definition$title))
  }
  if (!is.null(table_definition$caption) && nzchar(table_definition$caption) && !identical(table_definition$caption, table_definition$title)) {
    cat(sprintf("caption: %s\n", table_definition$caption))
  }
  if (!is.null(review$overall_plausibility)) {
    cat(sprintf("overall_plausibility: %.3f\n", as.numeric(review$overall_plausibility)))
  }
  notes <- as.character(unlist(review$notes %||% list(), use.names = FALSE))
  if (length(notes) > 0) {
    cat(sprintf("review notes: %s\n", paste(notes, collapse = " | ")))
  }
  cat("\n")

  cat("Rows\n")
  if (length(cleaned_rows) == 0) {
    cat("[No cleaned rows]\n\n")
  } else {
    for (i in seq_along(cleaned_rows)) {
      cat(sprintf("%2d | %s\n", i - 1L, paste(unlist(cleaned_rows[[i]], use.names = FALSE), collapse = " | ")))
    }
    cat("\n")
  }

  cat("Deterministic Variables\n")
  variables <- table_definition$variables %||% list()
  if (length(variables) == 0) {
    cat("[No variables]\n\n")
  } else {
    for (variable in variables) {
      label <- as.character(variable$variable_label %||% variable$variable_name %||% "")
      vtype <- as.character(variable$variable_type %||% "")
      row_start <- as.integer(variable$row_start %||% -1L)
      row_end <- as.integer(variable$row_end %||% -1L)
      cat(sprintf("%2d-%2d | %s | %s\n", row_start, row_end, vtype, label))
      levels <- variable$levels %||% list()
      if (length(levels)) {
        for (level in levels) {
          cat(sprintf(
            "      level row %2d | %s\n",
            as.integer(level$row_idx %||% -1L),
            as.character(level$level_label %||% level$level_name %||% "")
          ))
        }
      }
    }
    cat("\n")
  }

  cat("Variable Plausibility Review\n")
  review_variables <- review$variables %||% list()
  if (length(review_variables) == 0) {
    cat("[No rows]\n")
  } else {
    for (variable in review_variables) {
      label <- as.character(variable$variable_label %||% variable$variable_name %||% "")
      vtype <- as.character(variable$variable_type %||% "")
      row_start <- as.integer(variable$row_start %||% -1L)
      row_end <- as.integer(variable$row_end %||% -1L)
      score <- as.numeric(variable$plausibility_score %||% NA_real_)
      cat(sprintf("%2d-%2d | %s | %s | score=%.3f\n", row_start, row_end, vtype, label, score))
      levels <- variable$levels %||% list()
      if (length(levels) > 0) {
        cat("      levels:\n")
        for (level in levels) {
          cat(sprintf(
            "      row %2d | %s\n",
            as.integer(level$row_idx %||% -1L),
            as.character(level$level_label %||% level$level_name %||% "")
          ))
        }
      }
      note <- as.character(variable$plausibility_note %||% "")
      if (nzchar(note)) {
        cat(sprintf("      note: %s\n", note))
      }
      cat("\n")
    }
  }

  invisible(list(
    review = review,
    normalized_table = normalized_table,
    table_definition = table_definition
  ))
}

show_llm_variable_plausibility <- function(paper_dir, table_index = 0L) {
  outputs <- load_paper_outputs(paper_dir)
  review <- llm_variable_plausibility_review_by_index(outputs, table_index = table_index)
  normalized <- normalized_table_by_index(outputs, table_index = table_index)
  definition <- table_definition_by_index(outputs, table_index = table_index)
  show_variable_plausibility_review(review, normalized, definition)
}

summarize_llm_variable_plausibility_monitoring <- function(paper_dir, run_id = NULL) {
  loaded <- read_llm_variable_plausibility_monitoring(paper_dir, run_id = run_id)
  report <- loaded$monitoring
  items <- report$items %||% list()
  rows <- lapply(items, function(x) {
    data.frame(
      table_index = as.integer(x$table_index %||% -1L),
      table_id = as.character(x$table_id %||% ""),
      table_family = as.character(x$table_family %||% ""),
      eligible_for_review = as.logical(x$eligible_for_review %||% FALSE),
      status = as.character(x$status %||% ""),
      elapsed_seconds = as.numeric(x$elapsed_seconds %||% NA_real_),
      prompt_char_count = as.numeric(x$prompt_char_count %||% NA_real_),
      response_char_count = as.numeric(x$response_char_count %||% NA_real_),
      deterministic_variable_count = as.integer(x$deterministic_variable_count %||% 0L),
      attached_level_count = as.integer(x$attached_level_count %||% 0L),
      error_message = as.character(x$error_message %||% ""),
      stringsAsFactors = FALSE
    )
  })
  summary_df <- if (length(rows) == 0) {
    data.frame(
      table_index = integer(),
      table_id = character(),
      table_family = character(),
      eligible_for_review = logical(),
      status = character(),
      elapsed_seconds = numeric(),
      prompt_char_count = numeric(),
      response_char_count = numeric(),
      deterministic_variable_count = integer(),
      attached_level_count = integer(),
      error_message = character(),
      stringsAsFactors = FALSE
    )
  } else {
    do.call(rbind, rows)
  }

  cat(sprintf("Variable plausibility LLM monitoring summary: %s\n", loaded$run_dir))
  cat(sprintf("report_timestamp=%s provider=%s model=%s\n\n", report$report_timestamp %||% "", report$provider %||% "", report$model %||% ""))
  if (nrow(summary_df) == 0) {
    cat("[No rows]\n")
    return(invisible(summary_df))
  }
  print(summary_df, row.names = FALSE, right = FALSE)
  invisible(summary_df)
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
    cat(sprintf(
      "[%s] %s | %s | score=%s\n",
      passage$passage_id,
      passage$heading %||% "",
      passage$match_type %||% "",
      format(passage$score %||% NA)
    ))
    cat(passage$text %||% "", "\n\n", sep = "")
  }

  invisible(passages)
}
