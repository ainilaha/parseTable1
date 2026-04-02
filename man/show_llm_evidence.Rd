\name{show_llm_evidence}
\alias{show_llm_evidence}
\title{Show LLM evidence passages for one table}
\description{
Resolves \code{evidence_passage_ids} from the semantic LLM table definition back to the retrieved passage text.
}
\usage{
show_llm_evidence(paper_dir, table_index = 0L)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
  \item{table_index}{Zero-based table index matching parser output files such as \code{table_0_context.json}.}
}
\value{
Invisibly returns the semantic LLM table definition used for the display.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
show_llm_evidence("outputs/papers/cobaltpaper", table_index = 0L)
}
}
