"""survey.bounded — run a subprocess under a strict, reapable budget.

The single home for the `timeout --signal=INT --kill-after` wrapper: SIGINT at
the budget lets the tool's own handler (aut2ltl/proc.py) reap its GAP process
group, then SIGKILL after a 1s grace. Returns enough to classify the outcome
(completed / timed out / crashed) by exit code and wall time, agnostic to what
was run (front-end build, spot oracle, …).
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class BoundedResult:
    """Outcome of one bounded run. `rc` is None only if the backstop fired."""
    argv: List[str]
    rc: Optional[int]
    out: str
    err: str
    wall_s: float
    timed_out: bool


def _as_text(x: object) -> str:
    if isinstance(x, (bytes, bytearray)):
        return x.decode("utf-8", errors="replace")
    return x or ""  # type: ignore[return-value]


def run(argv: List[str], timeout: int, *, stdin: Optional[str] = None,
        cwd: Optional[Path] = None) -> BoundedResult:
    """Run `argv` under `timeout --signal=INT --kill-after=1 <timeout>`.

    SIGINT at the budget lets the tool's own handler reap its GAP process group;
    SIGKILL follows after a 1s grace. `subprocess.run`'s own timeout is only a
    backstop for `timeout` itself hanging (`timeout + 3`), so it SIGKILLs the
    python child directly — which WOULD orphan GAP — and we let the catchable
    SIGINT path above do the real reaping.

    A run that REACHED the budget (rc 124 from SIGINT / 137 from SIGKILL, or wall
    >= budget) is reported `timed_out`, whatever the exit code: the tool's own
    handler may exit with another code after reaping. A genuine crash exits FAST
    (wall < budget) and is left for the caller to classify by `rc`.
    """
    cmd = ["timeout", "--signal=INT", "--kill-after=1", str(timeout), *argv]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, input=stdin, capture_output=True, text=True,
            timeout=timeout + 3, cwd=str(cwd) if cwd is not None else None,
        )
    except subprocess.TimeoutExpired as te:
        return BoundedResult(argv, None, _as_text(te.stdout), _as_text(te.stderr),
                             time.monotonic() - t0, timed_out=True)
    wall_s = time.monotonic() - t0
    timed_out = proc.returncode in (124, 137) or wall_s >= timeout
    return BoundedResult(argv, proc.returncode, proc.stdout or "", proc.stderr or "",
                         wall_s, timed_out)
