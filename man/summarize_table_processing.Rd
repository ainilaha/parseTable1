\name{summarize_table_processing}
\alias{summarize_table_processing}
\title{Summarize per-table processing outcomes for one paper}
\description{
Prints one compact row per table showing processing status, failure stage, rescue-attempt counts,
and core semantic/value counts from the saved paper outputs.
}
\usage{
summarize_table_processing(paper_dir)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
}
\value{
Invisibly returns a data frame with one row per table.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
summarize_table_processing("outputs/papers/cobaltpaper")
}
}
