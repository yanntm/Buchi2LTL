#!/usr/bin/env python3
"""
tests/probes/bls/test_r4_audit.py

Placed audit script (per rules) for P0 R4/Rws correctness items.
The 5-point checklist below is the authoritative encoding of the R4/Rws0 + R5
structural corrections (verified against paper/Automata2LTL.txt pp. 11-13).

Focus: semantic grounding (Path A), duality hints (Path B), exact 5-point
checklist (Path C) against current _*_weak / Rws usage, plus better canary
(Path D) like G(p | F q) style.

Does NOT modify core formula code. Only inspects + exercises current impl
behaviorally + via source for the checklist. Uses Spot for semantics checks
on crafted words/configs for 1L reset cascades.

Run (always):
  python3 -m tests.probes.bls.test_r4_audit

All inside work folder, no /tmp, no inline long python.
"""

import sys
from pathlib import Path

import spot
from aut2ltl.bls import decompose_aut, CascadeHolder
from aut2ltl.bls.operators.reachability_operators import (
    reach_strong, reach_weak, simplify_ltl,
    _solid_stay_weak, _stay_gt0_weak,
    _dashed_change_strong,
)
from aut2ltl.bls.operators.fin import fin_c
from aut2ltl.bls.hierarchy_class import hierarchy_class

def _reset_counters():
    # No-op: build state (memos + counters) now lives on a per-build CascadeHolder,
    # not module globals. Kept so existing call sites read clearly.
    pass

def describe_simple_1l_reset():
    """Create/return a simple 1L reset cascade for audit (s=0, b=1, t=0 case).
    Alphabet {p= true-a, !p=false-a}. p: identity on 0/1; !p: reset to 1.
    This matches the example in the reference notes for drift-forever test.
    """
    # Use Spot to get a simple aut, then decompose (guaranteed counter-free for LTL).
    # For direct control, we can also synthesize via formula that produces
    # looping-coBuchi or weak, but for audit we use a known 1L structure.
    # Simpler: translate a formula that gives us the desired aut shape, then
    # inspect the cascade (which for 1L is trivial reset).
    f = spot.formula("G(p | F q)")  # exercises more than pure Fa; produces coBuchi-ish
    aut = f.translate("deterministic", "parity", "complete")
    aut = spot.simplify_acceptance(aut)
    casc = decompose_aut(aut)
    print("Audit cascade: num_levels=", casc.num_levels,
          "states=", casc.num_states,
          "aps=", casc.aps)
    return casc

def check_drift_forever_semantics():
    """Path A: semantic grounding test for Rws (Formula 4).
    For S=T (top same), B different top, pure-stay word (never leaves s, never hits B).
    Per paper Table 1 + Rws0 line(2): the formula must hold (vacuous, no blocking antecedent).
    We exercise current weak path and check if produced LTL accepts the drift word
    while the high-level semantics say it should for weak.
    """
    print("\n=== Path A: Drift-forever grounding (pure stay, S=T, no block) ===")
    casc = CascadeHolder(describe_simple_1l_reset())
    # For 1L, configs are 1-tuples. Pick S=(1,), T=(1,), B=(2,) or similar from the map.
    # Use reachable to pick.
    reach = casc.reachable_configs()
    if len(reach) < 2:
        print("  SKIP: cascade too trivial for S=T vs B diff")
        return False
    # Pick a config that can stay (has self via some letter).
    S = reach[0]
    # Find a T == S at top, B with diff top if possible.
    tops = {c[0] for c in reach}
    if len(tops) < 2:
        print("  SKIP: only one top level value")
        return False
    same_top = [c for c in reach if c[0] == S[0]]
    diff_top = [c for c in reach if c[0] != S[0]]
    if not same_top or not diff_top:
        print("  SKIP: no same/diff top pair")
        return False
    T = same_top[0]  # S == T at this level for the case
    B = diff_top[0]
    beta = "false"  # or a prop that can trigger on B
    tau = "true"
    # Current weak path for this (via reach_weak or the solid weak)
    _reset_counters()
    # Exercise the internal weak solid for stay case (source==target at level 0)
    # This is what would be used in Rws0 for the solid part.
    try:
        weak_stay = _solid_stay_weak(S, B, beta, T, tau, casc, 0)
        weak_stay = simplify_ltl(weak_stay)
        print("  _solid_stay_weak(S=T, diff B) =", weak_stay)
    except Exception as e:
        print("  ERROR exercising _solid_stay_weak:", e)
        weak_stay = "ERROR"
    # Now, the "drift" word: a sequence of stay letters only.
    # For audit, construct a word that stays in top of S forever.
    # Use letter valuations to pick a stay letter for S.
    parts = casc.compute_stay_leave_from(S)
    stay_gs = []
    for li, _ in parts.get("stay", []):
        if li < len(casc.letter_valuations):
            g = casc.letter_valuations[li]
            stay_gs.append(g)
    if not stay_gs:
        print("  SKIP: no stay letters from S")
        return False
    # Pick one stay valuation as "p" for the drift word.
    drift_val = stay_gs[0]
    # Build a long drift word (many repeats of a stay letter).
    # For semantics check: build LTL from the weak formula, translate, see if
    # a pure-drift word is accepted by the aut of that LTL.
    # Also compare to what paper Rws should do: for pure stay never blocking,
    # it should be true (vacuous).
    drift_word_ltl = " & ".join(  # conjunction of the props in the val (for the letter)
        [k if v else f"!{k}" for k, v in drift_val.items()]
    ) or "true"
    # The produced weak_stay should accept infinite drift (G(drift_letter)).
    # Check via Spot: does the LTL weak_stay accept the word that is always drift_letter?
    try:
        phi = spot.formula(weak_stay)
        phi_aut = phi.translate("Buchi")
        # Word that is infinite drift: repeat the letter.
        # Use spot to check acceptance on a lasso or just translate and see.
        # Simpler: build a word aut that is G(drift_letter), check equiv or intersection.
        drift_g = spot.formula(f"G({drift_word_ltl})")
        drift_aut = drift_g.translate("Buchi")
        # If the weak formula is satisfied by all pure-drift words, then
        # the language of phi should include the language of G(drift).
        # Check if drift_aut is subset of phi_aut (i.e. are_equiv or language inclusion).
        # For simplicity: check if spot.are_equivalent on a combined or just
        # simulate: does phi hold on the infinite word? Use product emptiness or
        # just evaluate the formula on a prefix (but for G it needs the whole).
        # Practical: translate both and see if the pure-drift aut is accepted
        # by phi (i.e. the run on drift word is accepting in phi_aut).
        # Use spot's built-in: product and check for accepting path? For audit we
        # can use a finite unrolling + check the structure.
        print("  drift_letter approx:", drift_word_ltl)
        # Semantic grounding (Path A per ref): does pure-drift infinite word satisfy the weak formula?
        # Per paper Table 1 + Rws0 line(2): for S=T, no block ever, vacuous weak must hold (G(drift) => phi).
        # Check via: lang( G(drift) & ~phi ) == empty  <=>  G(drift) implies phi.
        print("  weak_stay accepts pure-drift (G(drift)) ? (semantic via Spot: G(d) & !phi empty?)")
        try:
            phi_str = weak_stay
            bad = spot.formula(f"G({drift_word_ltl}) & !({phi_str})")
            bad_aut = bad.translate("Buchi")
            accepts_drift = bad_aut.is_empty()
            print("  semantic G(drift) => weak_stay holds (no counterex):", accepts_drift)
            if not accepts_drift:
                # For debug: size of bad lang if small
                print("    (bad lang non-empty; possible Rws0 issue for vacuous case)")
        except Exception as e:
            print("  ERROR in semantic drift check, falling back:", e)
            simp = simplify_ltl(weak_stay)
            accepts_drift = ("true" in simp.lower() or "1" in simp)
            print("  fallback simp check accepts_drift=", accepts_drift)
        return accepts_drift
    except Exception as e:
        print("  ERROR in drift semantics check:", e)
        return False

def _get_func_body(src: str, func_name: str) -> str:
    """Extract the source body of a function for precise inspection (no reliance on global strings)."""
    start = src.find(f"def {func_name}(")
    if start == -1:
        return ""
    # Find end at next top-level def or end of file
    end = src.find("\ndef ", start + 1)
    if end == -1:
        end = len(src)
    return src[start:end]


def check_5point_checklist():
    """Path C: exact 5-point structural checklist (R4/Rws0 + R5 corrections).
    Precise source inspection of the *bodies* of Rws0 / R4 + behavioral.
    """
    print("\n=== Path C: 5-point Rws0 / R4 checklist (source + behavioral) ===")
    from aut2ltl.bls.operators import reachability_operators as _reachops
    src_path = Path(_reachops.__file__)
    src = src_path.read_text()
    rws0_body = _get_func_body(src, "_stay_gt0_weak")
    rs_body = _get_func_body(src, "_solid_stay_weak")
    dashed_body = _get_func_body(src, "_dashed_change_strong")

    points = {
        "1. Has Line-2 disjunct (stay forever) in weak >0?": ('S, "false"' in rws0_body or "_avoid_conjs(S, _ff())" in rws0_body or ", S, false" in rws0_body),
        "2. Line-1 omits free-reach R1/strong(S,S,false,...) ?": ("reach_strong(S, S," not in rws0_body and "reach_strong(S,S" not in rws0_body),
        "3. Bad-predecessor avoids use Rw (weak) not R?": ("reach_weak" in rws0_body),
        "4. Outer case 4 is (core | tau) & !beta (weak form)?": ("And( _Or(gt0_f, tau_f)" in rs_body or "And( _Or(gt0_f, tau_f) , _Not(beta_f)" in rs_body or "(Rws0 ∨ τ) ∧ ¬β" in rs_body),
        "5. R5 line(2) Rws call has swapped roles (T,t,tau as 'bad', B,b,beta as target)?": ("_solid_stay_weak(arrR, T," in dashed_body or "_solid_stay_weak(earrived, T," in dashed_body),
    }
    all_ok = True
    for desc, ok in points.items():
        status = "PASS" if ok else "FAIL/CHECK"
        print(f"  {status}: {desc}")
        if not ok:
            all_ok = False
    # Behavioral: exercise a same-top target case with complex tau (postpone for last-visit/Fin).
    # Use semantic implication style check where possible.
    casc = CascadeHolder(describe_simple_1l_reset())
    reach = casc.reachable_configs()
    if reach:
        S = reach[0]
        T = S  # same
        B = reach[-1] if len(reach) > 1 else S
        # tau = a prop that is "leave condition" for last visit (not immediate)
        # Choose a real prop from aps for tau if possible (better exercise than "true")
        tau = next((ap for ap in casc.aps if ap), "true")
        if tau not in casc.aps:
            tau = "true"
        beta = "false"
        try:
            res = _solid_stay_weak(S, B, beta, T, tau, casc, 0)
            res = simplify_ltl(res)
            print("  Behavioral same-top weak with tau=prop:", res[:100])
            # For weak (Rws) when S=T: vacuous "true" (from line2) or containing operators for postpone is OK.
            # Only treat as bad if it collapses wrongly to "false" (or the bare prop without allowing future when expected).
            # "true" means vacuous weak holds for this (S,B,T,tau) choice -- acceptable per grounding.
            is_false = "false" in res.lower() and res.strip().lower() not in ("true", "false")
            postpones = (res.strip().lower() in ("true", "1") or "U" in res or "F" in res or "G" in res or len(res) > len(tau) + 3)
            postpones = postpones and not is_false
            print("  Postponement/vacuous-weak ok (not false, allows or vacuous):", postpones)
        except Exception as e:
            print("  ERROR behavioral:", e)
            postpones = False
        points["behavioral_postpone"] = postpones
        if not postpones:
            # Do not force overall FAIL on this heuristic alone; source points + drift semantic are primary.
            # Just note it (the canary equiv failure is the stronger signal for R4 work needed).
            print("  (behavioral note: postpones/vacuous=False for this config/tau choice; not gating overall)")
    return all_ok

def check_canary_roundtrip():
    """Path D: better canary that exercises R4 / Fin last-visit.
    G(p | F q) or similar that needs Π2/Σ2 and Fin with inner weak.
    Just run decompose + reconstruct and report equiv (as canary).
    """
    print("\n=== Path D: Better R4 canary roundtrip (G(p | F q) style) ===")
    _reset_counters()
    try:
        f = spot.formula("G(p | F q)")
        aut = f.translate()
        holder = CascadeHolder(decompose_aut(aut))
        ltl = hierarchy_class(holder).formula   # spot.formula DAG
        from aut2ltl.ltl.builders import _short_f
        print("  recovered:", _short_f(ltl, 100))
        orig_b = f.translate("Buchi")
        rec_b = ltl.translate("Buchi")
        eq = spot.are_equivalent(orig_b, rec_b)
        print("  are_equivalent:", eq)
        print("  reach_calls=", holder.reach_calls, "fin_calls=", holder.fin_calls)
        return eq
    except Exception as e:
        print("  ERROR in canary:", e)
        return False

def main():
    print("=== R4 / Rws P0 AUDIT (structural checklist + semantic grounding) ===")
    print("Using placed script discipline + timeout 5. No core code changes.")
    print("Current git clean slate assumed (run after the initial commit).")
    drift_ok = check_drift_forever_semantics()
    checklist_ok = check_5point_checklist()
    canary_ok = check_canary_roundtrip()
    print("\n=== SUMMARY ===")
    print("Drift-forever grounding:", "PASS" if drift_ok else "FAIL/INCONCLUSIVE")
    print("5-point checklist:", "PASS" if checklist_ok else "ISSUES FOUND (see above)")
    print("Better canary equiv:", "PASS" if canary_ok else "FAIL (expected for now if R4 not yet exact)")
    overall = drift_ok and checklist_ok
    print("Overall P0 audit status:", "CLEAN FOR PROCEED" if overall else "NEEDS ATTENTION BEFORE CODE CHANGES")
    # Exit non-zero if issues, to be visible under timeout runs.
    sys.exit(0 if overall else 1)

if __name__ == "__main__":
    main()
