#!/usr/bin/env python3
"""
kr/testing/probe_2l_rwith.py

Surgical probe for the 2L r_with failure on G(a -> X b), config C=(1,1)=iota.

Failing witness (in GT \\ r_with): w = (a&b); (!a&b); (!a&b); cycle{(a&b)}
 - visits state0=(1,1) at times 0,2,3 (finite, >=1); last visit t=3; psi holds there.
 - the run never leaves top 1 except... never (sink never entered): pure SOLID at level 0.

This probe decomposes, builds psi = !(C>0~>C), calls the failing
reach_strong((1,1) -> (1,1), tau=psi), then drills down:
  - does w satisfy the produced formula? its solid part? its dashed part?
  - for the solid+ last-step disjuncts: which conjunct rejects w?
Run: python3 kr/testing/probe_2l_rwith.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from kr import decompose_aut
import kr.reachability_operators as _ops
from kr.reachability_operators import (
    reach_strong, simplify_ltl,
    _solid_stay_strong, _stay_gt0_strong, _dashed_change_strong,
    _combined_letters_at_level, _letters_to_f, _str_f, _And, _X, _to_f,
)
from kr.fin import _uncond_reach_strict

WITNESS = "a & b; !a & b; !a & b; cycle{a & b}"


def word_satisfies(formula_str: str, word_str: str) -> str:
    """Does the lasso word satisfy the LTL formula?"""
    if formula_str in ("true",):
        return "True"
    if formula_str in ("false",):
        return "False"
    try:
        f = spot.formula(formula_str)
        aut = f.translate("Buchi")
        w = spot.parse_word(word_str, aut.get_dict())
        waut = w.as_automaton()
        return str(not spot.product(waut, aut).is_empty())
    except Exception as e:
        return f"err:{e}"[:80]


def main():
    f = spot.formula("G(a -> X b)")
    casc = decompose_aut(f.translate())
    print("configs:", casc.all_configs(), "| init:",
          casc.state_to_config.get(casc.original_aut.get_init_state_number()))

    _ops._clear_casc_registry()
    _ops._register_casc(casc)
    if hasattr(_ops, "_lru_reach_strong"):
        _ops._lru_reach_strong.cache_clear()

    C = (1, 1)
    r_gt0 = simplify_ltl(_uncond_reach_strict(C, C, casc))
    psi = simplify_ltl(f"!({r_gt0})")
    print("\npsi (no-return) =", psi)
    print("  w |= psi at t=3? (check: shift word)",
          word_satisfies(psi, "cycle{a & b}"))

    full = simplify_ltl(reach_strong(C, None, "false", C, psi, casc, 0))
    print("\nfull r_with:", "w |=", word_satisfies(full, WITNESS))

    solid = simplify_ltl(_solid_stay_strong(C, None, "false", C, psi, casc, 0))
    dashed = simplify_ltl(_dashed_change_strong(C, None, "false", C, psi, casc, 0))
    print("solid part:", "w |=", word_satisfies(solid, WITNESS))
    print("dashed part:", "w |=", word_satisfies(dashed, WITNESS))

    # Drill into solid+ last-step disjuncts at level 0
    print("\n--- solid+ level-0 last-step disjuncts ---")
    level = 0
    cls = _combined_letters_at_level(casc, level)
    s_val = C[level]
    stay_s = {}
    leave_s = {}
    for li, pre, arr in cls:
        key = (li, pre[level + 1:])
        if pre[level] == s_val and arr[level] == s_val:
            stay_s.setdefault(key, (li, pre, arr))
        elif pre[level] == s_val and arr[level] != s_val:
            leave_s.setdefault(key, (li, pre, arr))
    last_steps = [(k, v) for k, v in stay_s.items() if v[2][level:] == C[level:]]
    print(f"stay={len(stay_s)} leave={len(leave_s)} last_steps={len(last_steps)}")

    for key, (li, pre, arr) in last_steps:
        g_f = _letters_to_f(casc.letter_valuations[li], casc.aps)
        tail = _str_f(_And(g_f, _X(_to_f(psi))))
        print(f"\n  last-step letter={_str_f(g_f)} pre={pre} (T'={pre[level+1:]})")
        free = simplify_ltl(reach_strong(C, None, "false", pre, tail, casc, level + 1))
        print(f"    free-reach conjunct:  w |= {word_satisfies(free, WITNESS)}")
        for lkey, (lj, preL, arrL) in leave_s.items():
            eta_f = _letters_to_f(casc.letter_valuations[lj], casc.aps)
            av = simplify_ltl(reach_strong(C, preL, _str_f(eta_f), pre, tail, casc, level + 1))
            print(f"    leave-avoid (eta={_str_f(eta_f)}, L={preL[level+1:]}): "
                  f"w |= {word_satisfies(av, WITNESS)}")


if __name__ == "__main__":
    main()
