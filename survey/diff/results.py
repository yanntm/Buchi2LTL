"""survey.diff.results — quantitative diff of two survey RESULT CSVs.

Where ltl_diff compares LANGUAGES, this compares RUNS. Reads two CSVs written by
survey, keys both on the unique `source` column, and reports:

  1. KEY SETS — inputs absent left / absent right / common, and how many each
     side answered (produced a formula for). A "one side has fewer answers"
     discrepancy shows here.
  2. COMMON DIFF — validation regressions/fixes, result changes, technique
     changes, size movers and totals, computed STRICTLY on the common inputs.

Keyed by COLUMN NAME (pandas), so it survives schema reshuffles and leaves room
for richer analysis later. Worst-news-first; only changed rows are echoed.

    python -m survey.diff.results LEFT.csv RIGHT.csv
    python -m survey.diff.results LEFT.csv RIGHT.csv --top 5
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

import pandas as pd

KEY = "source"  # the unique provenance key every survey CSV carries


def _load(path: str) -> pd.DataFrame:
    """Survey CSV -> DataFrame indexed by the unique source key (last wins)."""
    df = pd.read_csv(path, dtype=str).fillna("")
    if KEY not in df.columns:
        sys.exit(f"{path}: no '{KEY}' column — not a survey CSV?")
    return df.drop_duplicates(subset=KEY, keep="last").set_index(KEY)


def _num(s: "pd.Series") -> "pd.Series":
    return pd.to_numeric(s, errors="coerce")


def _answered(df: pd.DataFrame) -> int:
    """Rows where aut2ltl produced a formula (result == LTL)."""
    if "result" not in df.columns:
        return 0
    return int((df["result"] == "LTL").sum())


def _pct(old: float, new: float) -> str:
    if old == 0:
        return "n/a" if new == 0 else "+inf"
    return f"{100.0 * (new - old) / old:+.1f}%"


def _print_sample(keys: List[str], cap: int) -> None:
    for k in keys[:cap]:
        print(f"    {k:.70s}")
    if len(keys) > cap:
        print(f"    ... +{len(keys) - cap} more")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Quantitative diff of two survey CSVs, keyed on the source column.")
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--top", type=int, default=10, help="max mover / sample rows to show")
    args = ap.parse_args()

    L, R = _load(args.left), _load(args.right)
    lk, rk = set(L.index), set(R.index)
    common = sorted(lk & rk)
    only_left = sorted(lk - rk)
    only_right = sorted(rk - lk)

    # --- stage 1: key sets -------------------------------------------------
    print("=== survey diff (keyed on source) ===")
    print(f"left ={args.left}   {len(lk)} inputs, {_answered(L)} answered")
    print(f"right={args.right}   {len(rk)} inputs, {_answered(R)} answered")
    print(f"key sets: {len(common)} common | "
          f"{len(only_left)} absent-from-right | {len(only_right)} absent-from-left")
    if only_left:
        print(f"  only in left ({len(only_left)}):")
        _print_sample(only_left, args.top)
    if only_right:
        print(f"  only in right ({len(only_right)}):")
        _print_sample(only_right, args.top)
    if not common:
        print("\nno common inputs — nothing to compare.")
        return 0

    # --- stage 2: diff on the common set -----------------------------------
    Lc, Rc = L.loc[common], R.loc[common]
    la, ra = _answered(Lc), _answered(Rc)
    note = "" if la == ra else "   <-- one side answered fewer"
    print(f"\non {len(common)} common inputs: answered  left {la}  right {ra}{note}")

    regressions: List[str] = []
    fixes: List[str] = []
    val_other: List[str] = []
    result_changes: List[str] = []
    tech_changes: List[str] = []
    movers: List[Tuple[int, str, str]] = []
    for k in common:
        o, n = Lc.loc[k], Rc.loc[k]
        ov, nv = o.get("validation", ""), n.get("validation", "")
        if ov != nv:
            line = f"  {k:30.30s} {ov or '-'} -> {nv or '-'}"
            if ov == "TRUE" and nv != "TRUE":
                regressions.append(line + ("   *** HARD ***" if nv == "FAIL" else ""))
            elif nv == "TRUE" and ov != "TRUE":
                fixes.append(line)
            else:
                val_other.append(line)  # SIZE<->TIMEOUT etc.: neither
        orr, nrr = o.get("result", ""), n.get("result", "")
        if orr != nrr:
            result_changes.append(f"  {k:30.30s} {orr or '-'} -> {nrr or '-'}")
        if o.get("technique", "") != n.get("technique", ""):
            tech_changes.append(
                f"  {k:30.30s} {o.get('technique', '-') or '-'} -> {n.get('technique', '-') or '-'}")
        od, nd = _num(pd.Series([o.get("dag")]))[0], _num(pd.Series([n.get("dag")]))[0]
        if pd.notna(od) and pd.notna(nd) and od != nd:
            movers.append((int(abs(nd - od)), k, f"DAG {int(od)} -> {int(nd)} ({_pct(od, nd):>7s})"))

    if regressions:
        print(f"\nVALIDATION REGRESSIONS ({len(regressions)}):")
        print("\n".join(regressions))
    if fixes:
        print(f"\nvalidation fixes ({len(fixes)}):")
        print("\n".join(fixes))
    if val_other:
        print(f"\nother validation changes ({len(val_other)}):")
        print("\n".join(val_other[: args.top]))
    if result_changes:
        print(f"\nresult changes ({len(result_changes)}):")
        print("\n".join(result_changes[: args.top]))
        if len(result_changes) > args.top:
            print(f"  ... +{len(result_changes) - args.top} more")
    if tech_changes:
        print(f"\ntechnique changes ({len(tech_changes)}):")
        print("\n".join(tech_changes[: args.top]))
        if len(tech_changes) > args.top:
            print(f"  ... +{len(tech_changes) - args.top} more")

    movers.sort(reverse=True)
    if movers:
        print(f"\ntop size movers (of {len(movers)} changed):")
        for _, k, detail in movers[: args.top]:
            print(f"  {k:30.30s} {detail}")

    od_dag, nd_dag = _num(Lc["dag"]).sum(), _num(Rc["dag"]).sum()
    od_tree, nd_tree = _num(Lc["tree"]).sum(), _num(Rc["tree"]).sum()
    print("\ntotals (common set):")
    print(f"DAG nodes : {int(od_dag)} -> {int(nd_dag)}  ({_pct(od_dag, nd_dag)})")
    print(f"tree nodes: {int(od_tree)} -> {int(nd_tree)}  ({_pct(od_tree, nd_tree)})")
    print(f"{len(regressions)} regression(s), {len(fixes)} fix(es), DAG {_pct(od_dag, nd_dag)} "
          f"(on {len(common)} common of {len(lk)}L/{len(rk)}R)")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
