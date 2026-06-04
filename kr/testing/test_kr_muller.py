#!/usr/bin/env python3
"""
kr/testing/test_kr_muller.py

Diagnostic for Muller acceptance handling vs current parity/SCC proxy.

Run from kr/ subdir or project:
  cd kr/testing
  python3 test_kr_muller.py

Explores:
- What Spot gives for get_acceptance() after different postprocess (parity, muller, etc.).
- Behavior of scc_info.is_rejecting_scc for different acc (including pure Muller).
- What our accepting_configs and _compute_good_muller_sets return.
- Whether we can support alpha that is general Muller (not just "SCC with acc" ).

This helps answer "what is stopping us from computing Muller ? for alpha not SCC"

All in kr/testing/ path, no /tmp, no long -c.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from kr import decompose_aut
from kr.reachability import _compute_good_muller_sets

def show_acc(aut, label):
    print(f"\n=== {label} ===")
    print("num_states:", aut.num_states())
    print("prop_deterministic:", aut.prop_deterministic())
    acc = aut.get_acceptance()
    print("get_acceptance():", acc)
    print("str(acc):", str(acc))
    try:
        print("acc.is_muller():", acc.is_muller())
    except:
        pass
    try:
        print("acc.is_parity():", acc.is_parity())
    except:
        pass
    try:
        si = spot.scc_info(aut)
        print("scc_count:", si.scc_count())
        for scci in range(si.scc_count()):
            rej = si.is_rejecting_scc(scci)
            states = [s for s in range(aut.num_states()) if si.scc_of(s) == scci]
            print(f"  SCC {scci}: rejecting={rej}, states={states}")
            # For Muller, may have more info?
    except Exception as e:
        print("scc_info err:", e)

def main():
    print("=== Muller diagnostic (pure kr path) ===")
    print("Project root:", PROJECT_ROOT)

    # Use a formula whose aut has interesting acc
    formulas = ["a", "Fa", "Ga", "G(p -> X q)", "F G a"]

    for fs in formulas:
        print(f"\n\n========== Formula: {fs} ==========")
        f = spot.formula(fs)

        # Loose translate (Buchi by default)
        aut_b = f.translate()
        show_acc(aut_b, "translate() default (Buchi-ish)")

        # Postprocess parity (what we force in decompose)
        aut_p = spot.postprocess(aut_b, "parity min even", "deterministic", "complete")
        show_acc(aut_p, "postprocess parity min even det complete (current kr norm)")

        # Try Muller postprocess (note: may not be supported as option in this Spot; try variants)
        for opt in ["Muller", "muller", "gen. Muller", "Muller,deterministic,complete"]:
            try:
                aut_m = spot.postprocess(aut_b, opt)
                show_acc(aut_m, f"postprocess {opt}")
                break
            except Exception as e:
                print(f"postprocess {opt} failed: {e}")

        # Try explicit Muller translate (Spot may use different)
        for t_opt in ["Muller", "muller"]:
            try:
                aut_mt = f.translate(t_opt)
                show_acc(aut_mt, f"translate({t_opt})")
                break
            except Exception as e:
                print(f"translate {t_opt} failed: {e}")

        # Other common postprocess to see resulting acc without forcing parity
        try:
            aut_dc = spot.postprocess(aut_b, "deterministic", "complete")
            show_acc(aut_dc, "postprocess deterministic complete (no parity)")
        except Exception as e:
            print("det complete post failed:", e)

        # Now, what our code does: decompose forces parity, then see good ms
        try:
            casc = decompose_aut(aut_b)  # will norm internally to parity
            print("\n--- After kr decompose_aut (internal parity norm) ---")
            print("casc num_levels:", casc.num_levels)
            reach = casc.reachable_configs() if hasattr(casc, 'reachable_configs') else []
            print("reachable_configs (BFS from init on config aut):", len(reach), "configs")
            acc_cfgs = casc.accepting_configs()
            print("accepting_configs():", acc_cfgs)
            good = _compute_good_muller_sets(casc)
            print("good_muller_sets (from _compute, now via pruned config graph SCC or basins):", [set(m) for m in good])

            # Demonstrate the new basin / decompose-scc=aN style helpers
            try:
                acc_sccs = casc.get_accepting_scc_indices() if hasattr(casc, 'get_accepting_scc_indices') else []
                print("accepting SCC indices (for aN-style decompose):", acc_sccs)
                for idx in acc_sccs[:2]:  # show first few
                    basin_confs = casc.configs_in_basin_of_scc(idx) if hasattr(casc, 'configs_in_basin_of_scc') else set()
                    print(f"  basin configs for accepting SCC {idx} (states leading to it + SCC): {basin_confs}")
            except Exception as e:
                print("basin demo err:", e)
        except Exception as e:
            print("decompose or good_ms err:", type(e).__name__, e)

    print("\n=== Observations / what stops Muller for non-SCC alpha ===")
    print("(Updated design: the Spot-normed det aut *is* our D; we only keep pre-norm aside for caller's final equiv check. See gap_bridge.py and cascade.py comments.)")
    print("See code in cascade.py:accepting_configs and reachability.py:_compute_good_muller_sets")
    print(" - decompose_aut always forces parity norm -> the D we work with has parity acc (Inf/Fin forms), not a general Muller set-of-sets.")
    print(" - Only special-cases 't'/'f' on D's acc; else relies on scc_info.is_rejecting_scc + has_acc_on_cycle (tuned for parity).")
    print(" - is_rejecting_scc works for parity/Buchi/Rabin; for a true general Muller alpha *on D* it may not directly enumerate the exact good subsets.")
    print(" - good_Ms are always 'full non-rejecting SCCs of D as sets' (mapped via h to configs) -> not proper subsets of an SCC, and not obtained by enumerating possible i.o. config sets and testing the projected state set against D's alpha.")
    print(" - For alpha that is 'not SCC' (general Muller on D where accepting depends on the exact i.o. set of states/configs, not just 'in a good SCC'), the current SCC-granular proxy is insufficient. We need the full family of good M' such that h(M') satisfies D's (Muller-equivalent) condition.")
    print(" - Paper is fine with Spot normalization as long as the resulting det aut (with its acc) is the D fed to decomp + reach + Fin + assembly (h is defined on its states). The 'identical semiautomaton' is now w.r.t. this D.")

if __name__ == "__main__":
    main()
