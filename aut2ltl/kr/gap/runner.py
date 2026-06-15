"""
kr/gap/runner.py — process-spawn service for the GAP bridge.

Everything that shells out to `gap` lives here: running a generated script and
probing whether a usable GAP (with SgpDec) is installed. Isolated from the pure
module API in bridge.py so the subprocess/tempfile machinery — and its failure
modes — stay in one place.
"""

from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ...proc import register_child, unregister_child, kill_child_group


def run_gap_script(
    script: str,
    *,
    gap_cmd: str = "gap",
    timeout: int = 180,
    workdir: Optional[Path] = None,
) -> str:
    """
    Write `script` to a temp file and execute `gap --no-window <script>`.

    Returns the captured stdout.  Stderr is logged but not returned.
    Raises on non-zero exit or timeout.
    """
    with tempfile.TemporaryDirectory(dir=workdir) as td:
        script_path = Path(td) / "decompose.gap"
        out_path = Path(td) / "cascade.out"

        script_path.write_text(script, encoding="utf-8")

        cmd = [gap_cmd, "--no-window", "--bare", str(script_path)]
        # No runaways: GAP is heavy and we never want it living on without us.
        # start_new_session=True drops it into its own process group (pgid==pid)
        # and we register that group, so on a timeout or an interrupt we take the
        # whole family down together rather than orphaning a multi-GB process.
        # (See aut2ltl/proc.py for the leash.)
        with open(out_path, "w", encoding="utf-8") as out_f:
            proc = subprocess.Popen(
                cmd,
                stdout=out_f,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            register_child(proc.pid)
            try:
                _, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                kill_child_group(proc.pid)
                proc.communicate()  # reap the killed group
                raise RuntimeError(f"GAP run timed out after {timeout}s") from None
            finally:
                unregister_child(proc.pid)

        captured = out_path.read_text(encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(
                f"GAP exited with code {proc.returncode}.\n"
                f"stderr (last 2000 chars):\n{(stderr or '')[-2000:]}\n"
                f"stdout head:\n{captured[:1500]}"
            )
        return captured


def check_gap_available(gap_cmd: str = "gap") -> bool:
    """Return True iff a runnable GAP that can LoadPackage("SgpDec") exists."""
    try:
        out = subprocess.run(
            [gap_cmd, "--no-window", "--bare", "-c",
             'if LoadPackage("SgpDec")=fail then Print("NO\n"); else Print("YES\n"); fi; QUIT;'],
            capture_output=True, text=True, timeout=15
        )
        return "YES" in out.stdout
    except Exception:
        return False
