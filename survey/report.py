"""survey.report — CSV emission and run summaries.

Defines the per-row CSV schema (input, provenance, technique, status, sizes,
timings, verdict), writes one CSV per --use config, and produces a compact
SUMMARY. Comparing two result CSVs lives in survey.diff.results; comparing two
LANGUAGES lives in survey.diff (ltl_diff).

Bones only — fold in survey_summary.sh.
"""
from __future__ import annotations

# TODO: Row schema + write_csv(rows, path)
# TODO: summarize(csv_path) -> str          (the SUMMARY.txt content)
