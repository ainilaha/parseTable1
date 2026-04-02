\name{compare_table_definitions}
\alias{compare_table_definitions}
\title{Compare deterministic and LLM table definitions}
\description{
Prints side-by-side comparisons of variables, levels, and columns for one table index.
}
\usage{
compare_table_definitions(paper_dir, table_index = 0L)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
  \item{table_index}{Zero-based table index matching parser output files such as \code{table_0_context.json}.}
}
\value{
Invisibly returns a list with \code{variables}, \code{levels}, and \code{columns} comparison data frames.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
compare_table_definitions("outputs/papers/cobaltpaper", table_index = 0L)
}
}
