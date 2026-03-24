\name{summarize_llm_semantic_monitoring}
\alias{summarize_llm_semantic_monitoring}
\title{Summarize semantic LLM debug monitoring}
\description{
Reads one timestamped semantic-LLM debug run and prints a compact per-table summary including status, elapsed time, prompt size, and error fields.
}
\usage{
summarize_llm_semantic_monitoring(paper_dir, run_id = NULL)
}
\arguments{
  \item{paper_dir}{Path to one paper output directory.}
  \item{run_id}{Optional timestamped debug-run directory name. If omitted, the latest run is used.}
}
\value{
Invisibly returns a data frame with one row per monitored table.
}
\examples{
\dontrun{
source("R/inspect_paper_outputs.R")
summarize_llm_semantic_monitoring("parse_runs/nephro_with_llm/papers/Nephro")
}
}
