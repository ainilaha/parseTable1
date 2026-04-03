pt1_null_coalesce <- function(x, y) {
  if (is.null(x) || length(x) == 0) {
    y
  } else {
    x
  }
}

pt1_read_json_file <- function(path) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("The 'jsonlite' package is required. Install it with install.packages('jsonlite').", call. = FALSE)
  }
  if (!file.exists(path)) {
    stop(sprintf("JSON file not found: %s", path), call. = FALSE)
  }
  json_text <- paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  jsonlite::fromJSON(json_text, simplifyVector = FALSE)
}

pt1_read_optional_json <- function(path) {
  if (!file.exists(path)) {
    return(NULL)
  }
  pt1_read_json_file(path)
}

pt1_unwrap_trace_payload <- function(x) {
  if (!is.null(x$payload) && is.list(x$payload)) {
    return(x$payload)
  }
  if (!is.null(x$interpretation) && is.list(x$interpretation)) {
    return(x$interpretation)
  }
  if (!is.null(x$response) && is.list(x$response)) {
    return(x$response)
  }
  x
}

pt1_unwrap_table_array <- function(x) {
  if (is.null(x)) {
    return(list())
  }
  if (is.null(names(x)) && length(x) > 0 && is.list(x[[1]])) {
    return(x)
  }
  list(x)
}

pt1_load_json_array <- function(path) {
  pt1_unwrap_table_array(pt1_unwrap_trace_payload(pt1_read_json_file(path)))
}
