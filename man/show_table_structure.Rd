\name{show_table_structure}
\alias{show_table_structure}
\title{Show rows, columns, and semantic table definition for one table}
\description{
Prints the normalized rows, semantic columns, and variable definitions for one
table in a saved paper output directory. When available, the header also shows
the processing status and terminal failure information from
\code{table_processing_status.json}.
}
\usage{
show_table_structure(
  paper_dir,
  table_index = 0L,
  variant = c("deterministic", "llm"),
  max_rows = NULL
)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
  \item{table_index}{Zero-based table index.}
  \item{variant}{Which table-definition variant to show, either \code{"deterministic"} or \code{"llm"}.}
  \item{max_rows}{Optional maximum number of normalized rows to print.}
}
\value{
Invisibly returns a list with \code{normalized_table} and \code{table_definition}.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
show_table_structure("outputs/papers/cobaltpaper", table_index = 1L)
show_table_structure("outputs/papers/cobaltpaper", table_index = 1L, max_rows = 20L)
}
}
