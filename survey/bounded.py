"""survey.bounded — run a subprocess under a strict, reapable budget.

The single home for the `timeout --signal=INT --kill-after` wrapper: SIGINT at
the budget lets the tool's own handler (aut2ltl/proc.py) reap its GAP process
group, then SIGKILL after a short grace. Returns enough to classify the outcome
(completed / TIMEOUT / crash) by exit code and wall time, agnostic to what was
run (front-end build, spot oracle, …).

Bones only — extract the core from tests/survey.py:run_build.
"""
from __future__ import annotations

# TODO: BoundedResult (rc, out, err, wall_s, timed_out)
# TODO: run(argv: list[str], timeout: int, *, stdin: Optional[str] = None,
#           cwd: Optional[Path] = None) -> BoundedResult
