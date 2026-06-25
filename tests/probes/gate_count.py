"""gate_count — measure the soundness-gate (`spot.are_equivalent`) traffic of a
default build, to see whether a per-(translator, Language) cache would help.

The daisy* family + partscc adopt a candidate only if `spot.are_equivalent(aut,
cand)` holds; on a non-daisy SCC `first_success` tries the gated peelers in order,
each paying a `translate(cand)` + `are_equivalent`, most DECLINED. With the
büchi-tower suffix sharing, the same (input automaton, candidate) pair is plausibly
recomputed many times — a `Memo` keyed on (translator, Language) would recover
exactly the REDUNDANT pairs.

This probe monkeypatches `spot.are_equivalent` (every gate calls it as
`spot.are_equivalent`, attribute-resolved at call time), drives the default recipe
in-process on ONE HOA, and reports:

  total gate calls, True/False split (denial rate),
  distinct (aut_fp, cand_fp) pairs -> redundant = total - distinct  (the headline),
  distinct input automata + the per-input call histogram (suffix re-visitation),
  gate wall time vs total build.

Usage (single input, run once, under the 15s cap):
    python3 tests/probes/gate_count.py <input.hoa>
Writes the report to tests/probes/logs/gate_count.<input>.txt and stdout.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from collections import Counter
from typing import List, Optional, Tuple

import spot

from aut2ltl.__main__ import ALL_SPECS
from aut2ltl.options import Options
from aut2ltl.language import Language
from aut2ltl.portfolio import build_portfolio


def _fp(aut: "spot.twa_graph") -> str:
    return hashlib.md5(aut.to_str("hoa").encode()).hexdigest()[:12]


def main(path: str, use: Optional[str] = None) -> None:
    calls: List[Tuple[str, str, bool]] = []
    gate_time = 0.0
    real_eq = spot.are_equivalent

    def counting_eq(aut, cand):  # type: ignore[no-untyped-def]
        nonlocal gate_time
        t0 = time.perf_counter()
        res = real_eq(aut, cand)
        gate_time += time.perf_counter() - t0
        calls.append((_fp(aut), _fp(cand), bool(res)))
        return res

    spot.are_equivalent = counting_eq
    try:
        lang = Language.of(spot.automaton(path))
        techs = [use] if use else None
        translator = build_portfolio(Options.from_specs(ALL_SPECS), techs)
        t0 = time.perf_counter()
        result = translator(lang)
        build_time = time.perf_counter() - t0
    finally:
        spot.are_equivalent = real_eq

    total = len(calls)
    trues = sum(1 for _, _, r in calls if r)
    falses = total - trues
    pairs = {(a, c) for a, c, _ in calls}
    redundant = total - len(pairs)
    auts = Counter(a for a, _, _ in calls)

    lines: List[str] = []
    lines.append(f"input            : {os.path.basename(path)}")
    lines.append(f"result DAG       : {result.formula.size() if result.ok else result.status}")
    lines.append(f"build wall       : {build_time:.3f}s   gate wall: {gate_time:.3f}s "
                 f"({100 * gate_time / build_time:.0f}% of build)")
    lines.append("")
    lines.append(f"gate calls       : {total}   (True {trues} adopted / False {falses} denied"
                 f" = {100 * falses / total:.0f}% denial)" if total else "gate calls       : 0")
    if total:
        lines.append(f"distinct (in,cand): {len(pairs)}   redundant: {redundant} "
                     f"({100 * redundant / total:.0f}% of calls are exact recomputes)")
        lines.append(f"distinct inputs  : {len(auts)}")
        lines.append("")
        lines.append("top re-visited input automata (aut_fp: #gate calls on it):")
        for fp, n in auts.most_common(8):
            lines.append(f"    {fp} : {n}")
    report = "\n".join(lines)

    os.makedirs("tests/probes/logs", exist_ok=True)
    tag = use or "default"
    out = f"tests/probes/logs/gate_count.{tag}.{os.path.basename(path)}.txt"
    with open(out, "w") as fh:
        fh.write(report + "\n")
    print(report)
    print(f"\n[written to {out}]")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("usage: python3 tests/probes/gate_count.py <input.hoa> [recipe]", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
