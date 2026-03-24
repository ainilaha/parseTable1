\name{compare_table_definition_runs}
\alias{compare_table_definition_runs}
\title{Compare table-definition variants across runs}
\description{
Prints side-by-side comparisons of variables, levels, and columns for one table index across two paper output directories or definition variants.
}
\usage{
compare_table_definition_runs(
  paper_dir_a,
  paper_dir_b,
  table_index = 0L,
  variant_a = "deterministic",
  variant_b = "llm",
  label_a = NULL,
  label_b = NULL
)
}
\arguments{
  \item{paper_dir_a}{Path to the left-hand paper output directory.}
  \item{paper_dir_b}{Path to the right-hand paper output directory.}
  \item{table_index}{Zero-based table index matching parser output files such as \code{table_0_context.json}.}
  \item{variant_a}{Which definition variant to read from \code{paper_dir_a}: \code{"deterministic"} or \code{"llm"}.}
  \item{variant_b}{Which definition variant to read from \code{paper_dir_b}: \code{"deterministic"} or \code{"llm"}.}
  \item{label_a}{Optional display label for the left-hand comparison block.}
  \item{label_b}{Optional display label for the right-hand comparison block.}
}
\value{
Invisibly returns a list with \code{variables}, \code{levels}, \code{columns}, and comparison metadata.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
compare_table_definition_runs(
  "parse_runs/nephro_no_llm/papers/Nephro",
  "parse_runs/nephro_with_llm/papers/Nephro",
  table_index = 0L,
  variant_a = "deterministic",
  variant_b = "llm",
  label_a = "no_llm",
  label_b = "with_llm_llm"
)
}
}
