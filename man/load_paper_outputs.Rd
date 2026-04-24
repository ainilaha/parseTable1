\name{load_paper_outputs}
\alias{load_paper_outputs}
\title{Load one paper output directory}
\description{
Reads the main parser outputs for one paper directory under \code{outputs/papers/<paper_stem>/}.
}
\usage{
load_paper_outputs(paper_dir)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
}
\value{
A list containing extracted tables, normalized tables, deterministic and optional LLM table definitions,
parsed tables, optional table-processing status records, paper markdown, paper sections, the paper-level
variable inventory, and per-table contexts.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
x <- load_paper_outputs("outputs/papers/cobaltpaper")
names(x)
}
}
