#!/usr/bin/env python3
"""
tests/survey.py — the single survey, driven through the FRONT END.

Unlike the retired probes (which wired straight into the engine API), this
survey reconstructs each formula by spawning the actual command-line tool
(`python3 -m aut2ltl <formula> --ltl`) and reading its stdout (the gated
formula) + stderr report (technique, DAG/tree sizes, build time). So it tests
exactly what a user runs.

For each formula, in two subprocesses with separate budgets (both 15s by
default — a blown budget IS a finding, reported, not waited on):

  1. BUILD   — the front-end tool. Subprocess isolation per formula is automatic
               (each is a fresh `-m aut2ltl` process).
  2. VERIFY  — a test-only spot oracle: classify (spot.mp_class) and, when the
               reconstructed formula is small enough to have been flattened,
               check spot.are_equivalent(original, reconstructed).

The equivalence check is deliberately NOT a CLI flag: it is a heavyweight
diagnosis the tool's clients should never pay for, so it lives here.

equiv verdicts:
  True            — verified equivalent (round-trip sound)
  FALSE           — verified NON-equivalent  ***A TRUE FAILURE***
  SPOT_TIMEOUT    — verification ran out of budget (NOT a failure; construction OK)
  UNVERIFIED_SIZE — formula too big to flatten (gated off), so not checkable here
  SPOT_ERR:...    — Spot could not translate (e.g. >32 acceptance sets)
build-phase outcomes (no equiv, no DAG): DECLINED / BUILD_TIMEOUT (construction
exceeded budget) / CRASH:... (the tool threw — a real defect)

Outputs a dense CSV (default tests/logs/survey_<timestamp>.csv) and prints the
overall report as the LAST lines of stdout.

Run from the project root:
    python3 tests/survey.py                      # the curated corpus
    python3 tests/survey.py "GFa & GFb" "FGa"     # specific formulas
    python3 tests/survey.py formulas.txt          # one formula per line (# comments)
    python3 tests/survey.py --use bls,sl          # pass --use through to the tool
    KR_SURVEY_TIMEOUT=30 python3 tests/survey.py  # widen the per-phase budget
    KR_SURVEY_CSV=out.csv python3 tests/survey.py # override the CSV output path
                                                  # (how survey_sweep.sh names per-config CSVs)

HOA-file inputs are planned (the tool already accepts them); this survey
currently feeds LTL strings only.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.survey_formulas import SURVEY_FORMULAS, KLASS_OF  # noqa: E402

# Per-phase budgets (separate, so a slow case tells us WHICH phase blocked).
BUILD_TIMEOUT = int(os.environ.get("KR_SURVEY_TIMEOUT", "15"))
EQUIV_TIMEOUT = int(os.environ.get("KR_SURVEY_EQUIV_TIMEOUT", "15"))

# Max chars of the reconstructed formula to keep in the CSV (the flat form can
# be huge even when it flattened under the tool's gate).
FORMULA_SHOWN = 80

MP_NAME = {"B": "bottom", "S": "safety", "G": "guarantee", "O": "obligation",
           "R": "recurrence", "P": "persistence", "T": "reactivity"}
MP_ORDER = {"B": 0, "S": 1, "G": 2, "O": 3, "R": 4, "P": 5, "T": 6}

# Test-only spot oracle: classify the original and (when a flattened
# reconstruction is supplied) check equivalence. Inputs travel via stdin — a
# multi-MB flat formula on argv dies with E2BIG.
_VERIFY_CHILD = '''
import sys, json
import spot
p = json.load(sys.stdin)
out = {}
orig = p["orig"]
is_hoa = p.get("is_hoa", False)
if is_hoa:
    # HOA-file original: the language is the automaton itself, so there is no
    # source formula to classify with mp_class. Load it once for equivalence.
    try:
        orig_aut = spot.automaton(orig)
        out["mp"] = "?"
    except Exception as e:
        orig_aut = None
        out["mp"] = "?"
        out["mp_err"] = str(e)[:90]
else:
    try:
        fo = spot.formula(orig)
        out["mp"] = spot.mp_class(fo)        # B/S/G/O/R/P/T
    except Exception as e:
        out["mp"] = "?"
        out["mp_err"] = str(e)[:90]
rec = p.get("rec")
if rec is None:
    out["equiv"] = None                      # nothing to verify (gated off / build failed)
else:
    try:
        if not is_hoa:
            orig_aut = spot.formula(orig).translate("Buchi")
        other = spot.formula(rec)
        if rec not in ("true", "false"):
            other = other.translate("Buchi")
        out["equiv"] = bool(spot.are_equivalent(orig_aut, other))
    except Exception as e:
        # Spot raises (not returns) on its limits; messages are multi-line, so
        # collapse whitespace before it reaches a CSV field. The >32-acceptance-
        # set wall is the standard case (a reconstruction with too many distinct
        # temporals) — give it a stable single-line tag.
        msg = " ".join(str(e).split())
        if "Too many acceptance sets" in msg:
            out["equiv"] = "SPOT_ERR:too-many-acceptance-sets"
        else:
            out["equiv"] = "SPOT_ERR:" + msg[:80]
print("VERIFY_JSON:" + json.dumps(out))
'''


def _is_hoa(s: str) -> bool:
    """True iff `s` is a path to an existing HOA automaton file (first non-blank
    line `HOA:`). Such inputs are fed whole to `--hoa`; an ordinary text file is
    still read as a one-formula-per-line list (see `_load_inputs`)."""
    p = Path(s)
    if not p.is_file():
        return False
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                return line.lstrip().startswith("HOA:")
    except OSError:
        return False
    return False


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
        elif key == "build time":
            out["build_s"] = val.rstrip("s")
    return out


def run_build(formula: str, use: Optional[str] = None,
              timeout: int = BUILD_TIMEOUT) -> Dict[str, object]:
    """Reconstruct `formula` via the front-end tool (passing `--use <use>`
    through when given). Returns the parsed report plus `status` (OK / DECLINED
    / BUILD_TIMEOUT / CRASH:...) and `rec` (the formula on stdout, or the
    `<unflattened ...>` placeholder). BUILD_TIMEOUT is a construction-budget
    overrun — flattening is size-gated in the tool, so the wall time is the
    cascade build, not rendering."""
    if _is_hoa(formula):
        tool = [sys.executable, "-m", "aut2ltl", "--hoa", formula]
    else:
        tool = [sys.executable, "-m", "aut2ltl", formula, "--ltl"]
    if use:
        tool += ["--use", use]
    # Strict per-phase budget with NO GAP runaway. `timeout` sends SIGINT at the
    # budget so the tool's interrupt handler (aut2ltl/proc.py) reaps GAP's whole
    # process group, then SIGKILLs after a 1s grace if the tool ignores SIGINT.
    # subprocess.run's own timeout is only a backstop for `timeout` itself
    # hanging: it SIGKILLs the python child directly, which WOULD orphan GAP, so
    # we give it slack and let the catchable-SIGINT path above do the reaping.
    cmd = ["timeout", "--signal=INT", "--kill-after=1", str(timeout), *tool]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout + 3, cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return {"status": f"BUILD_TIMEOUT>{timeout}s"}
    wall_s = time.monotonic() - t0
    # `timeout` reports 124 (SIGINT-killed at the budget) or 137 (SIGKILL after
    # the grace) — a construction overrun, not a tool crash.
    if proc.returncode in (124, 137):
        return {"status": f"BUILD_TIMEOUT>{timeout}s", "build_s": f"{wall_s:.3f}"}
    stdout = (proc.stdout or "").strip()
    stderr = proc.stderr or ""
    info = _parse_report(stderr)
    # External wall time is the fair, uniform measure across ALL outcomes (the
    # tool's own "build time" line covers only the cascade build, and the NOT_LTL
    # / decline paths print none). Override the parsed value with what we timed.
    info["build_s"] = f"{wall_s:.3f}"
    # A clean DECLINE is exit 1 WITH the tool's decline message; any other exit-1
    # (or other nonzero, or empty stdout) is the tool crashing — a real error, not
    # a decline (a DAG was NOT produced).
    if proc.returncode == 1 and "DECLINED" in stderr:
        info["status"] = "DECLINED"
        return info
    # Exit 3 is the NOT_LTL-family verdict (the language is (probably) not
    # LTL-definable — non-aperiodic transition monoid). Not a crash, not an answer.
    if proc.returncode == 3 and "NOT_LTL" in stderr:
        info["status"] = ("PROBABLY_NOT_LTL" if "PROBABLY_NOT_LTL" in stderr
                          else "NOT_LTL")
        return info
    if proc.returncode != 0 or not stdout:
        msg = (stderr or proc.stdout or "no output").strip().splitlines()
        info["status"] = "CRASH:" + (msg[-1][:90] if msg else "no output")
        return info
    info["status"] = "OK"
    info["rec"] = stdout
    return info


def run_verify(orig: str, rec: Optional[str],
               timeout: int = EQUIV_TIMEOUT) -> Dict[str, object]:
    """Classify `orig` and (when `rec` is a real flattened formula) check
    equivalence, in the test-only spot oracle subprocess."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _VERIFY_CHILD],
            input=json.dumps({"orig": orig, "rec": rec, "is_hoa": _is_hoa(orig)}),
            capture_output=True, text=True, timeout=timeout, cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return {"mp": "?", "equiv": "SPOT_TIMEOUT"}
    for line in (proc.stdout or "").splitlines():
        if line.startswith("VERIFY_JSON:"):
            return json.loads(line[len("VERIFY_JSON:"):])
    return {"mp": "?", "equiv": "SPOT_ERR:no marker"}


def survey_one(formula: str, use: Optional[str] = None) -> Dict[str, object]:
    """Full per-formula record: BUILD (front end) then VERIFY (spot oracle)."""
    # HOA inputs are file paths; record just the file name in the report/CSV
    # (the full path stays in `formula` for build/verify below).
    display = Path(formula).name if _is_hoa(formula) else formula
    rec_row: Dict[str, object] = {
        "formula": display,
        "class": KLASS_OF.get(formula, "?"),
        "mp": "?",
        "technique": "-",
        "dag_nodes": "",
        "temporals": "",
        "tree_nodes": "",
        "sharing": "",
        "build_s": "",
        "equiv": "",
        "reconstructed": "",
    }
    build = run_build(formula, use)
    rec_row["technique"] = build.get("technique", "-")
    for k in ("dag_nodes", "temporals", "tree_nodes", "sharing", "build_s"):
        if k in build:
            rec_row[k] = build[k]

    status = build["status"]
    if status != "OK":
        # build failure/decline: still classify (rec=None), surface the reason as equiv
        rec_row["mp"] = run_verify(formula, None).get("mp", "?")
        rec_row["equiv"] = status
        return rec_row

    # Defensive: a CSV field must never carry a newline (it would split the row);
    # a valid LTL formula has none, so this only guards against surprises.
    rec = str(build.get("rec", "")).replace("\n", " ").replace("\r", " ")
    checkable = None if rec.startswith("<unflattened") else rec
    verify = run_verify(formula, checkable)
    rec_row["mp"] = verify.get("mp", "?")
    if checkable is None:
        rec_row["equiv"] = "UNVERIFIED_SIZE"
    else:
        eq = verify.get("equiv")
        rec_row["equiv"] = {True: "True", False: "FALSE"}.get(eq, str(eq))
    rec_row["reconstructed"] = rec[:FORMULA_SHOWN] + ("…" if len(rec) > FORMULA_SHOWN else "")
    return rec_row


def _load_inputs(args: List[str]) -> List[str]:
    """Positional args are formulas, except an existing file is read one formula
    per line (# comments and blanks skipped). No args ⇒ the curated corpus."""
    if not args:
        return list(SURVEY_FORMULAS)
    formulas: List[str] = []
    for a in args:
        p = Path(a)
        if _is_hoa(a):
            formulas.append(a)               # a HOA file is ONE input, fed to --hoa
        elif p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    formulas.append(line)
        else:
            formulas.append(a)
    return formulas


# An ANSWER is a formula the tool reconstructed (build succeeded); the verdict
# then says whether the spot oracle could confirm it. declined / build_problem
# are NOT answers.
_ANSWER_CATS = ("validated", "spot_timeout", "unverified", "spot_err", "false")


def _category(equiv: str) -> str:
    if equiv == "True":
        return "validated"
    if equiv == "FALSE":
        return "false"
    if equiv == "SPOT_TIMEOUT":
        return "spot_timeout"
    if equiv == "UNVERIFIED_SIZE":
        return "unverified"
    if equiv == "DECLINED":
        return "declined"
    if equiv in ("NOT_LTL", "PROBABLY_NOT_LTL"):
        return "not_ltl"
    if equiv.startswith("SPOT_ERR"):
        return "spot_err"
    if equiv.startswith("BUILD_TIMEOUT"):
        return "build_timeout"   # construction exceeded budget (no DAG produced)
    return "build_crash"         # the tool actually threw (a real defect)


def _num(v: object) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _report(rows: List[Dict[str, object]], use: Optional[str]) -> List[str]:
    """The compact summary, returned as the last few lines (the CSV holds all the
    per-formula detail; this is just what `tail` carries). Build time is the
    construction time only — it does NOT include the spot equiv verification."""
    cat: Dict[str, int] = {}
    for r in rows:
        c = _category(str(r["equiv"]))
        cat[c] = cat.get(c, 0) + 1
    answers = [r for r in rows if _category(str(r["equiv"])) in _ANSWER_CATS]
    dag = sum(int(_num(r["dag_nodes"])) for r in answers)
    temp = sum(int(_num(r["temporals"])) for r in answers)
    build = sum(_num(r["build_s"]) for r in answers)
    label = use if use else "default"
    # FAIL == a verified non-equivalent formula was produced (a definite wrong
    # answer). Timeouts / size explosions / unverified are NOT failures.
    verdict = "FAIL" if cat.get("false", 0) else "SUCCESS"
    return [
        f"survey: {len(rows)} formulas  (--use {label})",
        f"answers {len(answers)}/{len(rows)}: validated {cat.get('validated', 0)}, "
        f"spot_timeout {cat.get('spot_timeout', 0)}, unverified {cat.get('unverified', 0)}, "
        f"spot_err {cat.get('spot_err', 0)}, false {cat.get('false', 0)}",
        f"declined {cat.get('declined', 0)}, not_ltl {cat.get('not_ltl', 0)}, "
        f"build_timeout {cat.get('build_timeout', 0)}, "
        f"build_crash {cat.get('build_crash', 0)}",
        f"totals over answers: DAG={dag} temporals={temp} build={build:.3f}s",
        verdict,
    ]


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="Survey the aut2ltl front end over a corpus of LTL formulas.")
    p.add_argument("inputs", nargs="*",
                   help="formulas, or a file (one formula per line); empty = curated corpus")
    p.add_argument("--use", metavar="T1,T2,...",
                   help="techniques to cite, passed through to the tool's --use")
    args = p.parse_args()

    formulas = _load_inputs(args.inputs)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs = PROJECT_ROOT / "tests" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    csv_path = Path(os.environ.get("KR_SURVEY_CSV", str(logs / f"survey_{ts}.csv")))

    # Per-formula detail goes to the CSV and a stderr progress trace; STDOUT
    # carries ONLY the compact summary (so a captured .txt stays terse).
    print(f"=== aut2ltl front-end survey: {len(formulas)} formulas "
          f"(build {BUILD_TIMEOUT}s, equiv {EQUIV_TIMEOUT}s"
          f"{', --use ' + args.use if args.use else ''}) ===", file=sys.stderr)
    hdr = (f"  {'formula':26s} {'mp':2s} {'tech':16s} "
           f"{'DAG':>6s} {'temp':>5s} {'build':>7s}  equiv")
    print(hdr, file=sys.stderr)
    print("  " + "-" * (len(hdr) - 2), file=sys.stderr)

    rows: List[Dict[str, object]] = []
    cols = ["formula", "class", "mp", "technique", "dag_nodes", "temporals",
            "tree_nodes", "sharing", "build_s", "equiv", "reconstructed"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for formula in formulas:
            row = survey_one(formula, args.use)
            rows.append(row)
            writer.writerow(row)
            fh.flush()
            bs = f"{row['build_s']}s" if row["build_s"] != "" else "-"
            print(f"  {formula:26.26s} {str(row['mp']):2s} "
                  f"{str(row['technique']):16.16s} "
                  f"{str(row['dag_nodes']):>6s} {str(row['temporals']):>5s} "
                  f"{bs:>7s}  {row['equiv']}", file=sys.stderr)
    print(f"CSV: {csv_path}", file=sys.stderr)

    for line in _report(rows, args.use):
        print(line)
    # exit non-zero iff a TRUE failure (verified non-equivalent) occurred
    return 1 if any(r["equiv"] == "FALSE" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
