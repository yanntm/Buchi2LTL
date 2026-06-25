#!/usr/bin/env python3
"""tests/probes/roundtrip/probe_shared_nodes.py — shared-subformula recoverability probe.

Question: inside the (heavily DAG-shared) formula the DEFAULT portfolio builds for a
HOA, are there SHARED subformulas whose language is recoverable AND comes back SMALLER
through a formula->automaton->formula round trip? If so, a cut targeting those internal
nodes (not just `toplevel(And)`) could shrink the result.

Method:
  1. Build F = default-portfolio formula for the HOA (survey's default settings),
     read into its hash-consed DAG in-process.
  2. Walk the DAG: pick nodes with >1 distinct PARENT (shared); for each, compute its
     SHARING = number of root->node paths (memoized topological pass) plus size /
     temporal / translatability.
  3. Back-and-forth DANCE on each shared subformula, via `survey` (default settings),
     under a severe per-node SIGKILL timeout. A subformula ABOVE the `Language.of`
     translate bound (`_guard_translation`, same constants) is NOT run — it is the
     un-recoverable case by construction, reported as such.

    python3 tests/probes/roundtrip/probe_shared_nodes.py <hoa> [TOPK=15] [TIMEOUT_S=5]
"""
from __future__ import annotations

import csv
import statistics
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

import spot

from aut2ltl.language import Language, UntranslatableLanguage
from aut2ltl.spotrun import _guard_translation
from aut2ltl.options import Options
from aut2ltl.bls.options import KR_OPTIONS
from aut2ltl.portfolio import build_portfolio
from aut2ltl.ltl.metrics import dag_node_count, temporal_node_count


def build_default_formula(hoa_path: str) -> Optional["spot.formula"]:
    """F = the default portfolio's formula for the HOA (survey's default settings)."""
    aut = spot.automaton(hoa_path)
    translator = build_portfolio(Options.from_specs(KR_OPTIONS), None)
    res = translator(Language.of(aut))
    return res.formula if res.ok else None


def walk_dag(
    root: "spot.formula",
) -> Tuple[Dict[int, "spot.formula"], Dict[int, Set[int]], Dict[int, int]]:
    """`(nodes, parent_ids, paths)` keyed by spot id: the distinct nodes, each node's
    set of distinct parents, and #root->node paths (counts multi-edges, so a node used
    twice under one parent is two paths)."""
    nodes: Dict[int, "spot.formula"] = {}
    parent_ids: Dict[int, Set[int]] = {}
    post: List[int] = []                                  # post-order (children before parents)

    def visit(g: "spot.formula") -> None:
        gid = g.id()
        if gid in nodes:
            return
        nodes[gid] = g
        for c in g:
            parent_ids.setdefault(c.id(), set()).add(gid)
            visit(c)
        post.append(gid)

    visit(root)
    paths: Dict[int, int] = {gid: 0 for gid in nodes}
    paths[root.id()] = 1
    for gid in reversed(post):                            # parents before children
        p = paths[gid]
        for c in nodes[gid]:
            paths[c.id()] += p
    return nodes, parent_ids, paths


def translatable(g: "spot.formula") -> bool:
    """Same bound as `Language.of`: would ltl2tgba be attempted on `g`, or refused?"""
    try:
        _guard_translation(g)
        return True
    except UntranslatableLanguage:
        return False


def dance(g: "spot.formula", timeout_s: int,
          recipe: str = "default") -> Tuple[str, Optional[int], str, float]:
    """Round-trip `g` through `survey` (recipe `recipe`, default settings), NO
    verification (we trust soundness — the 5s budget then times the BUILD alone, not
    the spot oracle), hard-killed at `timeout_s`. Returns
    `(result, dag_of_result, technique, wall_s)`; `result` is TIMEOUT/ERROR on failure."""
    argv = ["timeout", "-s", "KILL", str(timeout_s),
            "python3", "-m", "survey", "--ltl", str(g), "--no-verify"]
    if recipe and recipe != "default":
        argv += ["--use", recipe]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s + 3)
    except subprocess.TimeoutExpired:
        return ("TIMEOUT", None, "", time.monotonic() - t0)
    wall = time.monotonic() - t0
    rows = list(csv.reader(proc.stdout.splitlines()))
    for row in rows:
        if not row or row[0] == "input":
            continue
        # input,result,technique,build_s,formula,dag,temporals,tree,sharing,md5,validation,source
        result = row[1]
        technique = row[2] if len(row) > 2 else ""
        dag = int(row[5]) if len(row) > 5 and row[5].isdigit() else None
        return (result, dag, technique, wall)
    return ("ERROR", None, "", wall)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    hoa = sys.argv[1]
    topk = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    timeout_s = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    recipe = sys.argv[4] if len(sys.argv) > 4 else "default"

    f = build_default_formula(hoa)
    if f is None:
        print(f"default portfolio did not produce a formula for {hoa}")
        return 1

    nodes, parent_ids, paths = walk_dag(f)
    shared = [gid for gid in nodes if len(parent_ids.get(gid, ())) > 1]
    shared_t = [gid for gid in shared if translatable(nodes[gid])]
    shared_big = [gid for gid in shared if gid not in set(shared_t)]

    print(f"F: dag={dag_node_count(f)} temporal={temporal_node_count(f)} "
          f"root={f.kindstr()}")
    print(f"DAG: {len(nodes)} distinct nodes | shared (>1 parent): {len(shared)} "
          f"| of which translatable: {len(shared_t)}, too-large (skipped): {len(shared_big)}")
    if shared:
        sh = sorted((paths[g] for g in shared), reverse=True)
        print(f"sharing (root->node paths) over shared: max={sh[0]} "
              f"median={int(statistics.median(sh))} min={sh[-1]}")
    print()

    # ALL translatable shared nodes (topk<=0 means no cap), biggest first — blowups
    # come from the meatier nodes, so we want them surfaced, not hidden behind tiny hubs.
    cands = sorted(shared_t, key=lambda g: dag_node_count(nodes[g]), reverse=True)
    if topk > 0:
        cands = cands[:topk]
    print(f"=== dance on {len(cands)} shared+translatable nodes, biggest first "
          f"(survey --use {recipe}, --no-verify, SIGKILL {timeout_s}s) ===")
    print("(only SIZE-CHANGING + timeout rows shown; same-size & declined aggregated below)")
    print(f"{'dagG':>5} {'->':>2} {'dagG2':>7} {'par':>3} {'paths':>14} "
          f"{'wall':>6} {'result':>8}  technique")
    tally = {"smaller": 0, "same": 0, "bigger": 0, "declined": 0, "timeout": 0}
    same_time = 0.0                                       # total time spent confirming "no change"
    declined_time = 0.0                                   # total time spent on declines
    total_time = 0.0
    blowups: List[Tuple["spot.formula", int, int, str, float]] = []
    for gid in cands:
        g = nodes[gid]
        d0 = dag_node_count(g)
        result, d1, tech, wall = dance(g, timeout_s, recipe)
        total_time += wall
        if result == "LTL" and d1 is not None:
            key = "smaller" if d1 < d0 else ("same" if d1 == d0 else "bigger")
            tally[key] += 1
            if key == "same":                            # no modification: aggregate, don't print
                same_time += wall
                continue
            if key == "bigger":
                blowups.append((g, d0, d1, tech, wall))
        elif result in ("TIMEOUT", "ERROR"):
            tally["timeout"] += 1
        else:                                            # declined: aggregate, don't print
            tally["declined"] += 1
            declined_time += wall
            continue
        print(f"{d0:>5} {'->':>2} {str(d1) if d1 is not None else '-':>7} "
              f"{len(parent_ids[gid]):>3} {paths[gid]:>14} {wall:>6.2f} {result:>8}  {tech}")

    print()
    print(f"tally: smaller={tally['smaller']} same={tally['same']} bigger={tally['bigger']} "
          f"declined={tally['declined']} timeout={tally['timeout']}")
    print(f"UNCHANGED: {tally['same']} nodes recovered same-size, "
          f"{same_time:.1f}s spent confirming no change (of {total_time:.1f}s total dance time)")
    print(f"DECLINED:  {tally['declined']} nodes not recovered by the dance recipe, "
          f"{declined_time:.1f}s")
    if blowups:
        print(f"\n=== {len(blowups)} BLOWUP(s) (round trip returned BIGGER) ===")
        for g, d0, d1, tech, wall in sorted(blowups, key=lambda b: b[2] - b[1], reverse=True):
            print(f"  dag {d0} -> {d1}  (x{d1 / d0:.0f})  {wall:.2f}s  technique={tech}")
            print(f"    G = {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
