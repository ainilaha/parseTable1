\name{show_table_context}
\alias{show_table_context}
\title{Show retrieved paper context for one table}
\description{
Prints the retrieved passages for one table context, including passage IDs, headings, match types, and text.
}
\usage{
show_table_context(paper_dir, table_index = 0L, match_type = NULL)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
  \item{table_index}{Zero-based table index matching parser output files such as \code{table_0_context.json}.}
  \item{match_type}{Optional match type filter such as \code{"table_reference"}.}
}
\value{
Invisibly returns the filtered passage list.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
show_table_context("outputs/papers/cobaltpaper", table_index = 0L)
show_table_context("outputs/papers/cobaltpaper", table_index = 0L, match_type = "table_reference")
}
}
