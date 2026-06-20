"""survey.diff.results — quantitative diff of two survey RESULT CSVs.

Where ltl_diff compares LANGUAGES, this compares RUNS. Reads two CSVs written by
survey, keys both on the input, and reports:

  1. key sets — inputs absent left / absent right / common, and how many each
     side actually answered (built a DAG for);
  2. common diff — equivalence regressions / fixes, technique changes, size
     movers, totals — computed strictly on the common inputs.

For regression triage across runs or --use configs.

    python -m survey.diff.results A.csv B.csv

Bones only — migrate from tests/survey_diff.py.
"""
from __future__ import annotations

# TODO: diff_csv(a_path: Path, b_path: Path) -> str
# TODO: main() -> int
