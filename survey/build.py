"""survey.build — reconstruct one example under one technique, via the front end.

Spawns the actual command-line tool (`python -m aut2ltl ...`, passing `--use`
through when a technique is given) under `bounded`, then parses its stderr report
(technique, DAG/tree sizes, build time) and stdout (the gated formula). Tests
exactly what a user runs. Returns a `BuildResult` (status OK / DECLINED /
NOT_LTL / BUILD_TIMEOUT / CRASH, plus the reconstructed formula and metrics).

Bones only — migrate from tests/survey.py:run_build, atop survey.bounded.
"""
from __future__ import annotations

# TODO: BuildResult (status, rec, technique, sizes, build_s)
# TODO: build(example, technique: Optional[str], timeout: int) -> BuildResult
