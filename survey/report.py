"""survey.report — CSV emission, summaries, and CSV-vs-CSV result diffs.

The result-level reporting layer (distinct from survey.diff, which compares
LANGUAGES): defines the per-row CSV schema (input, provenance, technique,
status, sizes, timings, verdict), writes one CSV per --use config plus a compact
SUMMARY, and diffs two CSVs keyed on the input (regressions / fixes / size
movers) for regression triage.

Bones only — fold in tests/survey_diff.py and survey_summary.sh.
"""
from __future__ import annotations

# TODO: Row schema + write_csv(rows, path)
# TODO: summarize(csv_path) -> str          (the SUMMARY.txt content)
# TODO: diff_csv(a_path, b_path) -> str      (keyed on input; common-set diff)
