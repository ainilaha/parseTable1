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

clean_table_label <- function(label) {
  x <- trimws(gsub("\\s+", " ", label %||% ""))
  x <- sub(",\\s*(n\\s*\\(%\\)|n\\(%\\)|no\\.?\\s*\\(%\\)|mean\\s*[±\\+/-]?\\s*sd|mean\\s*\\(sd\\)|median\\s*\\(iqr\\))\\s*$",
           "", x, ignore.case = TRUE, perl = TRUE)
  x <- sub("\\s*\\(%\\)\\s*$", "", x, perl = TRUE)
  trimws(x)
}

infer_units <- function(label) {
  x <- trimws(gsub("\\s+", " ", label %||% ""))
  x <- sub(",\\s*(n\\s*\\(%\\)|n\\(%\\)|no\\.?\\s*\\(%\\)|mean\\s*[±\\+/-]?\\s*sd|mean\\s*\\(sd\\)|median\\s*\\(iqr\\))\\s*$",
           "", x, ignore.case = TRUE, perl = TRUE)
  m <- regexec("\\(([^()]*)\\)\\s*$", x, perl = TRUE)
  hit <- regmatches(x, m)[[1]]
  if (length(hit) < 2) {
    return(NULL)
  }
  units <- trimws(hit[2])
  if (!nzchar(units) || grepl("^%$", units) || grepl("^(sd|iqr|n)$", units, ignore.case = TRUE)) {
    return(NULL)
  }
  units
}

extract_variables_from_output_dir <- function(output_dir) {
  json_path <- file.path(output_dir, "final_interpretation.json")
  payload <- read_json_file(json_path)
  interpretation <- payload$interpretation %||% payload
  variables <- interpretation$variables %||% list()

  out <- lapply(variables, function(variable) {
    original <- variable$variable_name %||% variable$variable_label %||% ""
    original_levels <- vapply(
      variable$levels %||% list(),
      function(level) level$label %||% "",
      character(1)
    )
    list(
      name = clean_table_label(original),
      original = original,
      units = infer_units(original),
      levels = unname(vapply(original_levels, clean_table_label, character(1))),
      original_levels = unname(original_levels),
      type = variable$variable_type %||% NULL
    )
  })

  names(out) <- vapply(out, function(item) item$name %||% "", character(1))
  out
}

print_variable_structure <- function(x) {
  variables <- if (!is.null(x$variables) && is.list(x$variables)) x$variables else x
  for (variable in variables) {
    header <- variable$name %||% variable$original %||% ""
    if (!is.null(variable$units) && nzchar(variable$units)) {
      header <- sprintf("%s [units: %s]", header, variable$units)
    }
    cat(header, "\n", sep = "")
    cat("  original: ", variable$original %||% "", "\n", sep = "")
    if (!is.null(variable$type) && nzchar(variable$type)) {
      cat("  type: ", variable$type, "\n", sep = "")
    }
    if (length(variable$levels %||% character()) > 0) {
      cat("  levels:\n", sep = "")
      for (i in seq_along(variable$levels)) {
        cleaned <- variable$levels[[i]]
        original <- variable$original_levels[[i]] %||% cleaned
        if (!identical(cleaned, original)) {
          cat("    ", cleaned, " (original: ", original, ")\n", sep = "")
        } else {
          cat("    ", cleaned, "\n", sep = "")
        }
      }
    }
    cat("\n", sep = "")
  }
  invisible(x)
}
