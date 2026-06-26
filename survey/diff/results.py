"""survey.diff.results — compare two survey RESULT CSVs.

Where ltl_diff compares LANGUAGES, this compares RUNS. Reads two CSVs written by
survey, keys both on the unique `source` column, and reports in two tiers:

  CONSISTENCY (the gate, symmetric — order of the two args does not matter):
    * FAIL    — a run's formula was verified NON-equivalent to its own input.
    * CLASH   — the two runs contradict on one input: one produced an LTL formula,
                the other declared the language NOT_LTL. One of them is unsound.
    Only these set a non-zero exit. (We hold no certificate for NOT_LTL, so a bare
    NOT_LTL is not faulted — but LTL-vs-NOT_LTL between two runs is a red flag.)

  QUANTITATIVE (directional readout, never gates): the per-side breakdown mirrors
    survey's own SUMMARY taxonomy — two INDEPENDENT axes, never merged:
      * resolved  : LTL (a formula) vs not-LTL (a verdict) — both are answers — with
                    no-answer (declined / timeout / crash) broken out separately;
      * validated : TRUE / FAIL / not-checked, measured over the LTL rows ONLY.
    plus runtime (Σ build_s, the only timing the CSV carries — so labelled `build`,
    not "total runtime"), a TECHNIQUE shift (the left->right DIFF of which technique
    answered, how often — the global complement to the per-input technique changes),
    and the result / technique changes and size movers on the common inputs.
    left->right is measurement order, not a baseline verdict.

Compact by design: every example list is capped at `--top` (default 3) — only the
COUNT is ever shown in full (the count is the signal; the rows are a sample). The
`source` key is shown TAIL-anchored (a leading `…`, never a cut end) because the
discriminating part of a path/`file:line` is its end. `--formulas` appends each
shown size mover's left/right formula. Keyed by COLUMN NAME (pandas).

    python -m survey.diff.results LEFT.csv RIGHT.csv
    python -m survey.diff.results LEFT.csv RIGHT.csv --top 10 --formulas
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Tuple

import pandas as pd

KEY = "source"  # the unique provenance key every survey CSV carries
NOT_LTL = {"NOT_LTL", "PROBABLY_NOT_LTL"}  # a "no LTL formula exists" verdict
SRC_W = 34       # display width for the source key (tail-anchored)
TECH_FLOOR = 5   # min technique-shift rows shown (raise with --top)


def _load(path: str) -> pd.DataFrame:
    """Survey CSV -> DataFrame indexed by the unique source key (last wins)."""
    df = pd.read_csv(path, dtype=str).fillna("")
    if KEY not in df.columns:
        sys.exit(f"{path}: no '{KEY}' column — not a survey CSV?")
    return df.drop_duplicates(subset=KEY, keep="last").set_index(KEY)


def _num(s: "pd.Series") -> "pd.Series":
    return pd.to_numeric(s, errors="coerce")


def _tail(s: object, width: int = SRC_W) -> str:
    """Tail-anchored fixed-width: keep the END of the string (a leading `…` marks a
    cut head), then pad to `width`. The end is what discriminates a source path."""
    t = str(s)
    if len(t) > width:
        t = "…" + t[-(width - 1):]
    return f"{t:{width}s}"


def _breakdown(df: pd.DataFrame) -> Dict[str, float]:
    """The SUMMARY taxonomy as a dict — resolution counts on one axis, validation
    counts (over the LTL rows) on the other, plus the build-time sum. Mirrors
    `survey.report.summarize` so the diff and the SUMMARY never disagree."""
    rc = df["result"].value_counts() if "result" in df.columns else pd.Series(dtype=int)
    vc = df["validation"].value_counts() if "validation" in df.columns else pd.Series(dtype=int)
    g = lambda s, k: int(s.get(k, 0))
    return {
        "inputs": len(df),
        "ltl": g(rc, "LTL"),
        "not_ltl": g(rc, "NOT_LTL") + g(rc, "PROBABLY_NOT_LTL"),
        "declined": g(rc, "DECLINED"),
        "timeout": g(rc, "TIMEOUT"),
        "crash": g(rc, "CRASH"),
        "no_answer": g(rc, "DECLINED") + g(rc, "TIMEOUT") + g(rc, "CRASH"),
        "true": g(vc, "TRUE"),
        "fail": g(vc, "FAIL"),
        "not_checked": g(vc, "SIZE") + g(vc, "TIMEOUT") + g(vc, "ERROR"),
        "build": float(_num(df["build_s"]).sum()) if "build_s" in df.columns else 0.0,
    }


def _block(label: str, path: str, df: pd.DataFrame) -> Dict[str, float]:
    """Print one run's SUMMARY-style breakdown block and return its counts."""
    b = _breakdown(df)
    print(f"{label} = {path}   ({b['inputs']} inputs)")
    print(f"  resolved : {b['ltl']} LTL, {b['not_ltl']} not-LTL  |  "
          f"no-answer {b['no_answer']}  "
          f"(decl {b['declined']}, timeout {b['timeout']}, crash {b['crash']})")
    print(f"  validated: {b['true']} TRUE, {b['fail']} FAIL, {b['not_checked']} not-checked  "
          f"(of {b['ltl']} LTL)   build {b['build']:.1f}s")
    return b


def _tech_shift(Lc: pd.DataFrame, Rc: pd.DataFrame, cap: int) -> None:
    """A DIFF of technique usage on the common set: per technique whose count
    CHANGED, left_count -> right_count, biggest shift first. This is where a recipe
    change shows its hand — e.g. inv/scc decomp firing on more inputs (the global
    complement to the per-input technique changes)."""
    def _counts(df: pd.DataFrame) -> "pd.Series":
        t = df["technique"] if "technique" in df.columns else pd.Series(dtype=str)
        return t[t != ""].value_counts()
    lc, rc = _counts(Lc), _counts(Rc)
    rows = []
    for nm in set(lc.index) | set(rc.index):
        l, r = int(lc.get(nm, 0)), int(rc.get(nm, 0))
        if l != r:
            rows.append((abs(r - l), nm, l, r))
    if not rows:
        return
    rows.sort(reverse=True)
    suffix = f"  (showing {cap})" if len(rows) > cap else ""
    print(f"  technique shift: {len(rows)}{suffix}")
    for _, nm, l, r in rows[:cap]:
        print(f"    {l:3d} -> {r:3d}  ({r - l:+d})  {nm}")


def _pct(old: float, new: float) -> str:
    if old == 0:
        return "n/a" if new == 0 else "+inf"
    return f"{100.0 * (new - old) / old:+.1f}%"


def _section(title: str, items: List[str], cap: int) -> None:
    """A capped example list: the full count, then at most `cap` sample rows."""
    if not items:
        return
    suffix = f"  (showing {cap})" if len(items) > cap else ""
    print(f"  {title}: {len(items)}{suffix}")
    for line in items[:cap]:
        print(f"    {line}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compare two survey CSVs (consistency gate + quantitative), "
                    "keyed on the source column.")
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--top", type=int, default=3,
                    help="max example rows per list (counts always shown in full)")
    ap.add_argument("--formulas", action="store_true",
                    help="append each shown size mover's left/right formula")
    args = ap.parse_args()
    cap = args.top
    tech_cap = max(cap, TECH_FLOOR)

    L, R = _load(args.left), _load(args.right)
    lk, rk = set(L.index), set(R.index)
    common = sorted(lk & rk)
    only_left = sorted(lk - rk)
    only_right = sorted(rk - lk)

    # --- stage 1: per-side breakdown + key sets ----------------------------
    print("=== survey diff (keyed on source) ===")
    _block("left ", args.left, L)
    _block("right", args.right, R)
    print(f"key sets: {len(common)} common | "
          f"{len(only_left)} absent-from-right | {len(only_right)} absent-from-left")
    _section("only in left", [_tail(k) for k in only_left], cap)
    _section("only in right", [_tail(k) for k in only_right], cap)
    if not common:
        print("\nno common inputs — nothing to compare.")
        return 0

    def _verified(df: pd.DataFrame) -> bool:
        return ("validation" in df.columns
                and bool(df["validation"].isin(["TRUE", "FAIL"]).any()))

    lver, rver = _verified(L), _verified(R)
    if not (lver and rver):
        side = "left" if not lver else "right"
        print(f"note: {side} ran without verification — no FAIL/CLASH gate on it.")

    # --- stage 2: consistency gate (symmetric) -----------------------------
    Lc, Rc = L.loc[common], R.loc[common]
    fails: List[str] = []     # FAIL on either side (verified non-equivalent)
    clashes: List[str] = []   # LTL vs NOT_LTL between the two runs (one unsound)
    val_moves: List[str] = []  # quantitative: validation token changed (no FAIL)
    result_changes: List[str] = []
    tech_changes: List[str] = []
    movers: List[Tuple[int, str, str]] = []
    for k in common:
        o, n = Lc.loc[k], Rc.loc[k]
        ov, nv = o.get("validation", ""), n.get("validation", "")
        orr, nrr = o.get("result", ""), n.get("result", "")
        if ov == "FAIL" or nv == "FAIL":
            fails.append(f"{_tail(k)} left {ov or '-'} | right {nv or '-'}")
        if (orr == "LTL" and nrr in NOT_LTL) or (nrr == "LTL" and orr in NOT_LTL):
            clashes.append(f"{_tail(k)} left {orr or '-'} | right {nrr or '-'}")
        if ov != nv and ov != "FAIL" and nv != "FAIL":
            val_moves.append(f"{_tail(k)} {ov or '-'} -> {nv or '-'}")
        if orr != nrr:
            result_changes.append(f"{_tail(k)} {orr or '-'} -> {nrr or '-'}")
        if o.get("technique", "") != n.get("technique", ""):
            tech_changes.append(
                f"{_tail(k)} {o.get('technique', '-') or '-'} -> {n.get('technique', '-') or '-'}")
        od, nd = _num(pd.Series([o.get("dag")]))[0], _num(pd.Series([n.get("dag")]))[0]
        if pd.notna(od) and pd.notna(nd) and od != nd:
            movers.append((int(abs(nd - od)), k, f"DAG {int(od)} -> {int(nd)} ({_pct(od, nd):>7s})"))

    if fails or clashes:
        print(f"\nCONSISTENCY: {len(fails)} FAIL, {len(clashes)} CLASH   <-- UNSOUND")
        _section("FAIL — verified non-equivalent", fails, cap)
        _section("CLASH — LTL vs NOT_LTL", clashes, cap)
    else:
        print("\nCONSISTENCY: OK   (no FAIL, no LTL/NOT_LTL clash)")

    # --- stage 3: quantitative readout (left -> right; never gates) --------
    bl, br = _breakdown(Lc), _breakdown(Rc)
    na_flag = "   <-- right has more no-answers" if br["no_answer"] > bl["no_answer"] else ""
    print(f"\non {len(common)} common:  "
          f"LTL {bl['ltl']}->{br['ltl']}  "
          f"not-LTL {bl['not_ltl']}->{br['not_ltl']}  "
          f"no-answer {bl['no_answer']}->{br['no_answer']}  |  "
          f"TRUE {bl['true']}->{br['true']}  FAIL {bl['fail']}->{br['fail']}{na_flag}")

    _section("validation moves", val_moves, cap)
    _section("result changes", result_changes, cap)
    _section("technique changes", tech_changes, cap)

    movers.sort(reverse=True)
    if movers:
        suffix = f"  (showing {cap})" if len(movers) > cap else ""
        print(f"  size movers: {len(movers)}{suffix}")
        for _, k, detail in movers[:cap]:
            print(f"    {_tail(k)} {detail}")
            if args.formulas:
                print(f"        L: {Lc.loc[k].get('formula', '') or '-'}")
                print(f"        R: {Rc.loc[k].get('formula', '') or '-'}")

    _tech_shift(Lc, Rc, tech_cap)

    od_dag, nd_dag = _num(Lc["dag"]).sum(), _num(Rc["dag"]).sum()
    od_tree, nd_tree = _num(Lc["tree"]).sum(), _num(Rc["tree"]).sum()
    print(f"  runtime  build {bl['build']:.1f}s -> {br['build']:.1f}s ({_pct(bl['build'], br['build'])})"
          f"   DAG {int(od_dag)}->{int(nd_dag)} ({_pct(od_dag, nd_dag)})"
          f"  tree {int(od_tree)}->{int(nd_tree)} ({_pct(od_tree, nd_tree)})")

    verdict = "UNSOUND" if (fails or clashes) else "consistent"
    print(f"\n{verdict}: {len(fails)} FAIL, {len(clashes)} CLASH | "
          f"LTL {bl['ltl']}->{br['ltl']}, not-LTL {bl['not_ltl']}->{br['not_ltl']}, "
          f"no-answer {bl['no_answer']}->{br['no_answer']}, "
          f"build {_pct(bl['build'], br['build'])}, DAG {_pct(od_dag, nd_dag)}")
    return 1 if (fails or clashes) else 0


if __name__ == "__main__":
    sys.exit(main())
