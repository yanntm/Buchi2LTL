"""survey.report — row assembly and run summaries.

The CSV is the pipeline, read left to right, and a row short-circuits: an
aut2ltl block (what the tool produced) then a validation block (what the spot
oracle said). Once a stage stops, the later cells stay empty. `row()` merges the
two blocks — the aut2ltl block printed from a BuildResult, the validation block
a single token the caller (survey.run) decided.
"""
from __future__ import annotations

import csv
from collections import Counter
from typing import Dict, List, Sequence, TextIO

from survey.build import BuildResult

COLS: List[str] = ["input", "result", "technique", "build_s", "formula",
                   "dag", "temporals", "tree", "sharing", "validation", "source"]
FORMULA_SHOWN = 80


def _result_token(status: str) -> str:
    """BuildResult.status -> the `result` column token."""
    if status == "OK":
        return "LTL"
    if status.startswith("BUILD_TIMEOUT"):
        return "TIMEOUT"
    if status.startswith("CRASH"):
        return "CRASH"
    return status            # DECLINED / NOT_LTL / PROBABLY_NOT_LTL


def row(display: str, br: BuildResult, validation: str,
        source: str = "") -> Dict[str, object]:
    """Merge the aut2ltl result block (from a BuildResult) with the validation
    token into one CSV row. Non-LTL rows leave the formula/size cells empty.
    `display` is the readable label (basename / formula text, may collide);
    `source` is the unique provenance key (relative path, file:line, --ltl:k)."""
    r: Dict[str, object] = {c: "" for c in COLS}
    r["input"] = display
    r["source"] = source
    r["result"] = _result_token(br.status)
    r["technique"] = br.technique or ""
    r["build_s"] = br.build_s or ""
    if br.status == "OK":
        rec = str(br.rec or "").replace("\n", " ").replace("\r", " ")
        r["formula"] = rec[:FORMULA_SHOWN] + ("…" if len(rec) > FORMULA_SHOWN else "")
        for src, dst in (("dag_nodes", "dag"), ("temporals", "temporals"),
                         ("tree_nodes", "tree"), ("sharing", "sharing")):
            if src in br.report:
                r[dst] = br.report[src]
    r["validation"] = validation
    return r


def write_csv(rows: Sequence[Dict[str, object]], fileobj: TextIO,
              cols: Sequence[str] = COLS) -> None:
    writer = csv.DictWriter(fileobj, fieldnames=list(cols))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


def _num(v: object) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def summarize(rows: Sequence[Dict[str, object]], label: str) -> List[str]:
    """Compact per-technique summary (the CSV holds the per-input detail).
    FAIL iff a verified non-equivalent (`validation == FAIL`) occurred."""
    res = Counter(str(r.get("result")) for r in rows)
    val = Counter(str(r.get("validation")) for r in rows if r.get("validation"))
    ltl = res.get("LTL", 0)
    not_ltl = res.get("NOT_LTL", 0) + res.get("PROBABLY_NOT_LTL", 0)
    fails = val.get("FAIL", 0)
    not_checked = val.get("SIZE", 0) + val.get("TIMEOUT", 0) + val.get("ERROR", 0)

    lines = [
        f"survey: {len(rows)} inputs  (--use {label})",
        f"aut2ltl: {ltl} LTL, {not_ltl} not-LTL  |  "
        f"declined {res.get('DECLINED', 0)}, timeout {res.get('TIMEOUT', 0)}, "
        f"crash {res.get('CRASH', 0)}",
    ]
    if val.get("TRUE", 0) or fails or not_checked:
        lines.append(f"validation of {ltl} LTL: {val.get('TRUE', 0)} TRUE, "
                     f"{fails} FAIL, {not_checked} not checked (size/timeout/error)")
    elif val.get("OFF", 0):
        lines.append(f"validation: OFF ({ltl} LTL unverified)")

    dag = sum(int(_num(r.get("dag"))) for r in rows if r.get("result") == "LTL")
    temp = sum(int(_num(r.get("temporals"))) for r in rows if r.get("result") == "LTL")
    build = sum(_num(r.get("build_s")) for r in rows)
    lines.append(f"totals: DAG={dag} temporals={temp} build={build:.3f}s")
    lines.append("FAIL" if fails else "SUCCESS")
    return lines
