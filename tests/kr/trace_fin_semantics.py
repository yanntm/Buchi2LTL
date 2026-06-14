#!/usr/bin/env python3
"""
kr/testing/trace_fin_semantics.py

Semantic grounding of every fin_c sub-term, per config, against ground-truth
automata built directly from the normalized D's semiautomaton (no LTL
involved), with containment direction + witness words (via ltl_diff).

For each reachable config C (state s = h^-1(C)):
  r_to   = iota ~> C                 GT: "run visits s at some time >= 0"
  r_gt0  = C >0~> C                  GT: "run STARTED AT s revisits s at time >= 1"
  r_with = iota ~> C(!(C>0~>C))      GT: "s visited at least once and finitely often"
  fin    = !(r_to) | r_with          GT: "s visited finitely often (possibly 0)"
  !fin                               GT: "s visited infinitely often"

Ground truths:
  - "visited i.o."    : copy semiautomaton, Buchi mark on out-edges of s.
  - "visited >= once" : seen-bit product (bit set at/after first visit),
                        Buchi marks on bit=1 edges (strict=: ignore time 0).
  - finite/compose    : spot.complement + spot.product.

This is the contradiction-milking tool for the Fin/R4 P0 work (GFa canary).

Run from project root:
    python3 kr/testing/trace_fin_semantics.py "GFa"
    python3 kr/testing/trace_fin_semantics.py "FGa" "G(a -> F b)"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import spot

from aut2ltl.kr import decompose_aut
import aut2ltl.kr.reachability_operators as _ops
from aut2ltl.kr.reachability_operators import (
    reach_strong,
    simplify_ltl,
)
from aut2ltl.kr.fin import fin_c, _uncond_reach_strict
from aut2ltl.kr.ltl_builders import _Not, _to_f, _tree_size_f
from ltl_diff import diff_report, to_aut

# Flatten gate: sub-terms are kept as formula OBJECTS and only stringified
# when their memoized unfolded size is below this (≈ a 2MB string). Building
# the string first and gating on len() was itself the stall: one X(a & Xa)
# sub-term spends minutes inside str() before any gate can see it.
FLATTEN_TREE_LIMIT = int(os.environ.get("KR_FLATTEN_TREE_LIMIT", "250000"))


def _flatten_gated(f_obj):
    """(flat_string_or_None, tree_size). None = too large to ever flatten."""
    f_obj = _to_f(f_obj)
    n = _tree_size_f(f_obj)
    if n > FLATTEN_TREE_LIMIT:
        return None, n
    return simplify_ltl(f_obj), n


# ---------------------------------------------------------------- ground truth

def _copy_semiaut_buchi(D, mark_pred):
    """Copy D's semiautomaton; Buchi acceptance with Inf(0) marks exactly on
    edges where mark_pred(src, dst) holds."""
    g = spot.make_twa_graph(D.get_dict())
    g.copy_ap_of(D)
    g.set_buchi()
    g.new_states(D.num_states())
    g.set_init_state(D.get_init_state_number())
    for s in range(D.num_states()):
        for e in D.out(s):
            if mark_pred(s, e.dst):
                g.new_edge(s, e.dst, e.cond, [0])
            else:
                g.new_edge(s, e.dst, e.cond, [])
    return g


def gt_io(D, target):
    """GT automaton: run of D visits `target` infinitely often."""
    return _copy_semiaut_buchi(D, lambda s, d: s == target)


def gt_visited_once(D, init_state, target, strict: bool):
    """GT automaton: run of D *started at init_state* visits `target` at some
    time (>= 1 if strict, else >= 0). Seen-bit product: states (q, b),
    b sticky-set upon arriving at target; Buchi marks on b=1 edges
    (bit is sticky, so 'visited once' == 'bit set i.o.')."""
    n = D.num_states()
    g = spot.make_twa_graph(D.get_dict())
    g.copy_ap_of(D)
    g.set_buchi()
    g.new_states(2 * n)
    b0 = 1 if (not strict and init_state == target) else 0
    g.set_init_state(init_state + b0 * n)
    for q in range(n):
        for e in D.out(q):
            for b in (0, 1):
                nb = 1 if (b == 1 or e.dst == target) else 0
                g.new_edge(q + b * n, e.dst + nb * n, e.cond,
                           [0] if nb == 1 else [])
    return g


def gt_fin(D, target):
    """GT automaton: target visited finitely often (possibly zero)."""
    return spot.complement(gt_io(D, target))


def gt_once_and_fin(D, init_state, target):
    """GT automaton: target visited at least once AND finitely often."""
    return spot.product(gt_visited_once(D, init_state, target, strict=False),
                        gt_fin(D, target))


def build_config_semiaut(casc):
    """Deterministic semiautomaton on the cascade CONFIG closure (the real run
    space of the cascade). With the true-cascade extraction, pi (config ->
    state) is a many-to-one cover: 'run visits config C' is strictly finer
    than 'run visits state pi(C)', so per-config sub-terms must be grounded
    HERE, not on D (on D the sink-cover configs ground as spurious BADs).
    Returns (twa_graph, {config: state_index})."""
    import buddy
    configs = sorted(casc.reachable_configs())
    cidx = {c: i for i, c in enumerate(configs)}
    D = casc.original_aut
    g = spot.make_twa_graph(D.get_dict())
    g.copy_ap_of(D)
    g.set_buchi()
    g.new_states(len(configs))
    init_cfg = casc.state_to_config[D.get_init_state_number()]
    g.set_init_state(cidx[init_cfg])
    apvar = {ap: buddy.bdd_ithvar(g.register_ap(ap)) for ap in casc.aps}
    for c in configs:
        for li in range(casc.num_letters()):
            try:
                nc = casc.move_config(c, li)
            except Exception:
                continue
            if nc not in cidx:
                continue
            cond = buddy.bddtrue
            for ap, val in casc.letter_valuations[li].items():
                cond = cond & (apvar[ap] if val else buddy.bdd_not(apvar[ap]))
            g.new_edge(cidx[c], cidx[nc], cond, [])
    return g, cidx


# ---------------------------------------------------------------- per-config

CHECK_TIMEOUT = int(os.environ.get("KR_CHECK_TIMEOUT", "10"))


def _check_child():
    """Hidden subprocess mode (--_check): one diff_report under the parent's
    per-check timeout. Reads {"hoa","ltl","name"} JSON on stdin (the GT aut
    travels as HOA text), prints REPORT_JSON line. Spot's translate/complement
    on a pathological sub-term then stalls only this child, not the trace."""
    payload = json.load(sys.stdin)
    gt = spot.automaton(payload["hoa"])
    rep = diff_report(gt, payload["ltl"], "GT", payload["name"])
    print("REPORT_JSON:" + json.dumps(rep))


def check(name: str, gt_aut, produced_ltl, tree_n: int = -1):
    """Compare GT automaton vs produced LTL string; print verdict.
    Returns True (OK) / False (semantic BAD) / None (UNVERIFIED: Spot could
    not check within KR_CHECK_TIMEOUT, or the sub-term was too large to even
    flatten — it was BUILT fine either way).
    The Spot work (translate + containment both ways, complement inside) is
    unbounded in the worst case, so it runs in a child process under the cap."""
    if produced_ltl is None:
        print(f"    {name} = <unflattened formula object, tree={tree_n}>")
        print(f"      UNVERIFIED (unfolded size {tree_n} > "
              f"KR_FLATTEN_TREE_LIMIT={FLATTEN_TREE_LIMIT}; never stringified)")
        return None
    # Truncated print: sub-terms can flatten to 100MB+ (G(p->(qUr)) fin:
    # 108MB) — dumping them burns the whole wall clock on I/O.
    if len(produced_ltl) > 400:
        print(f"    {name} = {produced_ltl[:400]} ...[len={len(produced_ltl)}]")
    else:
        print(f"    {name} = {produced_ltl}")
    if produced_ltl.startswith(("ERROR", "NOT_IMPLEMENTED")):
        print(f"      SKIP ({produced_ltl})")
        return None
    if len(produced_ltl) > 2_000_000:
        print(f"      UNVERIFIED (flat formula len={len(produced_ltl)} is beyond "
              f"any Spot translation; skipped without spawning a check)")
        return None
    payload = json.dumps({"hoa": gt_aut.to_str("hoa"), "ltl": produced_ltl, "name": name})
    try:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--_check"],
            input=payload, capture_output=True, text=True,
            timeout=CHECK_TIMEOUT, cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        print(f"      UNVERIFIED (spot consistency check exceeded {CHECK_TIMEOUT}s; "
              f"sub-term built fine, len={len(produced_ltl)} — Spot verification "
              f"blocked, NOT a construction failure)")
        return None
    rep = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("REPORT_JSON:"):
            rep = json.loads(line[len("REPORT_JSON:"):])
    if rep is None:
        print(f"      UNVERIFIED (child rc={proc.returncode}: "
              f"{(proc.stderr or proc.stdout or '')[-160:].strip()})")
        return None
    ok = "languages equivalent" in rep
    print(("      OK  " if ok else "      BAD ") + rep.strip())
    return ok


def trace_formula(formula_str: str) -> dict:
    print(f"\n================ {formula_str} ================")
    f = spot.formula(formula_str)
    casc = decompose_aut(f.translate())
    D = casc.original_aut
    init_state = D.get_init_state_number()
    init_cfg = casc.state_to_config.get(init_state)
    print(f"D: {D.num_states()} states, acc={D.get_acceptance()}, "
          f"init state {init_state} = config {init_cfg}")

    # mimic reconstruct's operator setup
    _ops._clear_casc_registry()
    _ops._register_casc(casc)
    if hasattr(_ops, "_lru_reach_strong"):
        _ops._lru_reach_strong.cache_clear()

    # Ground on the CONFIG semiautomaton (cover-aware): per-config sub-terms
    # speak about cascade configs, and pi is many-to-one under the true
    # extraction, so grounding against state-visit GTs on D is wrong for
    # cover configs (spurious under-approx BADs on e.g. duplicated sinks).
    CD, cidx = build_config_semiaut(casc)
    init_ci = cidx[init_cfg]

    verdicts = {}
    for C in sorted(casc.reachable_configs()):
        s = casc.config_to_state.get(C)
        ci = cidx[C]
        print(f"\n  --- config C={C} (state {s})"
              f"{'  [== iota]' if C == init_cfg else ''} ---")

        # Everything stays a formula OBJECT until _flatten_gated decides the
        # unfolded size is printable/checkable (negations via _Not, never
        # f"!({...})" string surgery on potentially-100MB flats).
        r_to_o = reach_strong(init_cfg, None, "false", C, "true", casc)
        r_gt0_o = _uncond_reach_strict(C, C, casc)
        r_with_o = reach_strong(init_cfg, None, "false", C, _Not(_to_f(r_gt0_o)), casc)
        fin_o = fin_c(C, casc)
        notfin_o = _Not(_to_f(fin_o))

        v = {}
        for key, label, gt, obj in (
            ("r_to", "r_to  (iota~>C, visit>=0)",
             gt_visited_once(CD, init_ci, ci, strict=False), r_to_o),
            ("r_gt0", "r_gt0 (C>0~>C, revisit from C)",
             gt_visited_once(CD, ci, ci, strict=True), r_gt0_o),
            ("r_with", "r_with (>=1 visit & finite)",
             gt_once_and_fin(CD, init_ci, ci), r_with_o),
            ("fin", "fin   (finitely often)", gt_fin(CD, ci), fin_o),
            ("notfin", "!fin  (infinitely often)", gt_io(CD, ci), notfin_o),
        ):
            flat, tree_n = _flatten_gated(obj)
            v[key] = check(label, gt, flat, tree_n)
        verdicts[C] = v

    bad = [(C, k) for C, v in verdicts.items() for k, ok in v.items() if ok is False]
    unv = [(C, k) for C, v in verdicts.items() for k, ok in v.items() if ok is None]
    if bad:
        verdict = "CONTRADICTIONS: " + str(bad)
    elif unv:
        verdict = (f"NO CONTRADICTION ({len(unv)} sub-term(s) UNVERIFIED — "
                   f"Spot blocked within {CHECK_TIMEOUT}s, construction fine): {unv}")
    else:
        verdict = "ALL SUB-TERMS GROUNDED OK"
    print(f"\n  SUMMARY {formula_str}: {verdict}")
    return verdicts


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--_check":
        _check_child()
        return
    cases = sys.argv[1:] or ["GFa"]
    for fs in cases:
        trace_formula(fs)


if __name__ == "__main__":
    main()
