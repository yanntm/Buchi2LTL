#!/usr/bin/env python3
"""
kr/testing/test_kr_zoom.py

Full trace / "zoom in" for a given LTL formula on the pure paper algebraic KR path
(Boker-Lehtinen-Sickert FoSSaCS 2022 construction via cascade, reach ops, Fin, Muller assembly).

Now reusable: pass formula as argument (default "Fa" to demonstrate).
Run from project root:
  python3 kr/testing/test_kr_zoom.py
  python3 kr/testing/test_kr_zoom.py "Fa"
  python3 kr/testing/test_kr_zoom.py "G(p -> X q)"

This traces (for the target formula):
- Original aut from Spot translate()
- After decompose_aut: normalized aut (our D), cascade details
- Reachable configs (BFS on config aut)
- Accepting configs
- Muller sets (good Ms) via the current compute (config SCCs + basins)
- The pruned config automaton structure
- Reconstruction (with KR_TRACE=1 for reach/fin details)
- Final LTL and equiv check

All output via prints (no /tmp files).
Uses the kr/testing path discipline.
"""

import os
import sys
import argparse
from pathlib import Path

# Set trace early (before any kr imports that read KR_TRACE)
os.environ['KR_TRACE'] = '1'

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot
from aut2ltl.kr import decompose_aut, reconstruct_bls
from aut2ltl.kr.reachability import _compute_good_muller_sets

def describe_aut(aut, label):
    print(f"\n=== {label} ===")
    print("num_states:", aut.num_states())
    print("init_state:", aut.get_init_state_number())
    print("acc:", aut.get_acceptance())
    print("deterministic:", bool(aut.prop_deterministic()))
    print("complete:", bool(aut.prop_complete()))
    try:
        hoa = aut.to_str('hoa')
        print("HOA (first 20 lines):")
        for i, line in enumerate(hoa.splitlines()):
            if i < 20:
                print("  ", line)
            else:
                print("  ... (truncated)")
                break
    except Exception as e:
        print("HOA dump err:", e)
    si = spot.scc_info(aut)
    print("SCC count:", si.scc_count())
    for i in range(si.scc_count()):
        rej = si.is_rejecting_scc(i)
        states = [s for s in range(aut.num_states()) if si.scc_of(s) == i]
        print(f"  SCC {i}: rejecting={rej}, states={states}")
        # Check for acc in this SCC
        has_acc = False
        for s in states:
            for e in aut.out(s):
                if e.dst in states and list(e.acc.sets()):
                    has_acc = True
                    break
            if has_acc: break
        print(f"         has_acc_cycle={has_acc}")

def main():
    parser = argparse.ArgumentParser(
        description="KR full trace/zoom-in script (pure paper algebraic path). "
                    "Shows automata, cascade, muller sets, pruned config aut, "
                    "reconstructions (with KR_TRACE), and equiv for the target formula."
    )
    parser.add_argument(
        "formula", nargs="?", default="Fa",
        help="LTL formula string to zoom in on (default: Fa for demonstration)"
    )
    args = parser.parse_args()
    formula_str = args.formula

    print(f"=== FULL TRACE FOR FORMULA '{formula_str}' (pure paper path) ===")
    print("Project root:", PROJECT_ROOT)

    f = spot.formula(formula_str)
    print("\n=== Input formula:", f)

    # 1. Original aut (pre-norm, what caller usually has)
    aut_orig = f.translate()
    describe_aut(aut_orig, "Original aut from f.translate() (pre-norm, Buchi-ish)")

    # 2. Decompose (this does the norm internally)
    print("\n=== Calling decompose_aut(aut_orig) ===")
    casc = decompose_aut(aut_orig)
    print("Cascade created.")
    print("casc:", casc)
    print("num_levels:", casc.num_levels)
    print("levels:", [(l.index, l.size, l.kind, l.structure) for l in casc.levels])
    print("num_states (of D):", casc.num_states)
    print("state_to_config (h):", casc.state_to_config)
    print("config_to_state:", casc.config_to_state)
    print("aps:", casc.aps)
    print("num_letters (2^|AP|):", casc.num_letters())

    # The normalized D aut
    aut_d = casc.original_aut
    describe_aut(aut_d, "Normalized D (casc.original_aut after parity min-even det complete)")

    # 3. Reachable configs (BFS on config aut from init)
    print("\n=== reachable_configs() (BFS exploration of config automaton from init) ===")
    reach = casc.reachable_configs()
    print("reachable configs (sorted):", reach)
    print("count:", len(reach))

    # 4. Accepting configs (on the D, pruned to reachable)
    print("\n=== accepting_configs() ===")
    acc = casc.accepting_configs()
    print("accepting configs:", acc)

    # 5. Good Muller sets (the key for assembly)
    print("\n=== good_muller_sets via _compute_good_muller_sets (uses config graph SCCs + basins) ===")
    good_ms = _compute_good_muller_sets(casc)
    print("good_ms:", [set(m) for m in good_ms])
    print("count:", len(good_ms))

    # Pruned config aut details
    print("\n=== build_pruned_config_aut() (the actual config automaton we analyze) ===")
    g = casc.build_pruned_config_aut()
    if g:
        print("config aut num_states:", g.num_states())
        print("config aut init:", g.get_init_state_number())
        print("config aut acc:", g.get_acceptance())
        # Describe its SCCs
        si = spot.scc_info(g)
        print("config aut SCC count:", si.scc_count())
        for i in range(si.scc_count()):
            rej = si.is_rejecting_scc(i)
            conf_idxs = [k for k in range(g.num_states()) if si.scc_of(k) == i]
            print(f"  config SCC {i}: rejecting={rej}, config indices={conf_idxs}")
            # map back to actual configs
            confs = [reach[k] for k in conf_idxs]
            print(f"    corresponding configs: {confs}")
    else:
        print("No pruned config aut available.")

    # 6. Reconstruction
    print("\n=== Calling reconstruct_bls(casc) (with KR_TRACE=1 for steps) ===")
    print("(Traces from reach_strong, fin_c, etc. should appear above if enabled)")
    ltl = reconstruct_bls(casc)   # spot.formula DAG
    from aut2ltl.kr.ltl_builders import _str_f_gated
    print("\n=== Recovered LTL:", _str_f_gated(ltl))

    # 7. Equiv check (translate straight from the formula object)
    print("\n=== Equivalence check ===")
    orig_b = f.translate("Buchi")
    rec_b = ltl.translate("Buchi")
    eq = spot.are_equivalent(orig_b, rec_b)
    print("are_equivalent(original Buchi, recovered):", eq)

    print(f"\n=== END OF TRACE FOR '{formula_str}' ===")
    print(f"Summary for '{formula_str}':")
    print("  - See full output above for: original+normed automata (describe_aut),")
    print("    cascade details (levels, state_to_config, etc.), reachable_configs,")
    print("    accepting_configs, good_muller_sets (_compute_good_muller_sets),")
    print("    build_pruned_config_aut + its SCCs, reconstruction under KR_TRACE,")
    print("    recovered LTL, and Spot are_equivalent check.")
    print("  - The script is now reusable via command-line formula argument.")
    print("  - For 'a' this previously demonstrated the solid-guard + bdd fixes; for 'Fa'")
    print("    (and others) it shows the 1L or multi-level paper construction in detail.")
    print("  - Traces from reach_strong/fin_c/assembly appear when KR_TRACE=1 (set at top).")

if __name__ == "__main__":
    main()
