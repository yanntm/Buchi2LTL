"""survey.build — reconstruct one example under one technique, via the front end.

Spawns the actual command-line tool (`python -m aut2ltl ...`, passing `--use`
through when a technique is given) under `bounded`, then parses its stderr report
(technique, DAG/tree sizes, build time) and stdout (the gated formula). Tests
exactly what a user runs.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, Optional

from aut2ltl import bounded


@dataclass
class BuildResult:
    """Outcome of reconstructing one input. `rec` is the stdout formula (or the
    `<unflattened ...>` placeholder) only when `status == "OK"`; `witness` is the
    serialized NOT_LTL counting family (the stdout line) on a (probably-)not-LTL
    verdict, or None when none was produced."""
    status: str            # OK / DECLINED / NOT_LTL / PROBABLY_NOT_LTL / BUILD_TIMEOUT>Ns / CRASH:...
    rec: Optional[str] = None
    technique: Optional[str] = None
    report: Dict[str, object] = field(default_factory=dict)
    build_s: Optional[str] = None
    witness: Optional[str] = None


def _strip_kind(stdout: str, kind: str) -> str:
    """Drop the front end's `<kind>: ` result tag, leaving the bare payload (the
    LTL formula, or the witness line). Tolerant if the tag is already absent."""
    prefix = f"{kind}: "
    return stdout[len(prefix):] if stdout.startswith(prefix) else stdout


def _parse_report(stderr: str) -> Dict[str, object]:
    """Pull technique / DAG nodes / tree nodes / sharing / build time out of the
    front end's stderr report (`key : value` lines)."""
    out: Dict[str, object] = {}
    for line in stderr.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "technique":
            out["technique"] = val
        elif key == "DAG nodes":
            out["dag_nodes"] = int(val)
        elif key == "temporals":
            out["temporals"] = int(val)
        elif key == "tree nodes":
            out["tree_nodes"] = int(val)
        elif key == "sharing":
            out["sharing"] = val.rstrip("x")
        elif key == "dag md5":
            out["md5"] = val
        elif key == "build time":
            out["build_s"] = val.rstrip("s")
    return out


def build(value: str, *, is_hoa: bool, technique: Optional[str],
          timeout: int) -> BuildResult:
    """Reconstruct `value` (an HOA file path, or an LTL formula string) by
    spawning the front end, passing `--use technique` through when given.

    Status: a run that reached the budget is BUILD_TIMEOUT (the cascade build,
    not rendering — flattening is size-gated in the tool). Exit 1 WITH the tool's
    decline message is DECLINED; exit 3 with NOT_LTL is the (probably-)not-LTL
    verdict; any other nonzero / empty stdout is a CRASH (no DAG produced).
    """
    if is_hoa:
        tool = [sys.executable, "-m", "aut2ltl", "--hoa", value]
    else:
        tool = [sys.executable, "-m", "aut2ltl", value, "--ltl"]
    tool += ["--dagmd5"]  # report a stable DAG fingerprint (the `md5` column)
    if technique:
        tool += ["--use", technique]

    res = bounded.run(tool, timeout)
    if res.timed_out:
        return BuildResult(status=f"BUILD_TIMEOUT>{timeout}s",
                           build_s=f"{res.wall_s:.3f}")

    stdout = (res.out or "").strip()
    stderr = res.err or ""
    report = _parse_report(stderr)
    # External wall time is the fair, uniform measure across all outcomes.
    build_s = f"{res.wall_s:.3f}"
    technique_out = report.get("technique")  # type: ignore[assignment]

    if res.rc == 1 and "DECLINED" in stderr:
        return BuildResult("DECLINED", technique=technique_out, report=report,
                           build_s=build_s)
    if res.rc == 3 and "NOT_LTL" in stderr:
        status = "PROBABLY_NOT_LTL" if "PROBABLY_NOT_LTL" in stderr else "NOT_LTL"
        # stdout is the kind-tagged witness line ("NOT_LTL: p=... v=[...] ..."); strip
        # the tag to the bare payload, or None when the tool produced no witness.
        witness = _strip_kind(stdout, "NOT_LTL") or None
        return BuildResult(status, technique=technique_out, report=report,
                           build_s=build_s, witness=witness)
    if res.rc != 0 or not stdout:
        msg = (stderr or res.out or "no output").strip().splitlines()
        return BuildResult("CRASH:" + (msg[-1][:90] if msg else "no output"),
                           report=report, build_s=build_s)
    return BuildResult("OK", rec=_strip_kind(stdout, "LTL"), technique=technique_out,
                       report=report, build_s=build_s)
