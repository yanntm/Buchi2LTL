# kr/ — Krohn-Rhodes / Holonomy Cascade Path

This subtree implements the algebraic translation from (counter-free deterministic) automata to LTL following:

Udi Boker, Karoliina Lehtinen, Salomon Sickert.
"On the Translation of Automata to Linear Temporal Logic". FoSSaCS 2022.

The approach is systematic and algebraic: no pattern matching on SCCs, terminal components, or other shape-based rules (those are in the separate heuristic engine under `buchi2ltl/`). Everything is driven by the Krohn-Rhodes reset cascade (holonomy decomposition via SgpDec + GAP), the Stay/Leave/Enter partitions of letters per level, the configuration mapping, and the inductive definition of the five reachability formulas + Fin(C) + Muller assembly.

See `kr/algorithm.md` for the authoritative construction description, `kr/STATUS.md` for gaps and current practical status.

## Pipeline

Spot automaton
→ normalize (inside `decompose_aut`) to deterministic complete minimized parity (min even)
→ extract generators (one per concrete letter in 2^|AP|)
→ self-contained GAP script (SgpDec HolonomyCascadeSemigroup + AsCoords; robust 1-state handling)
→ run via `gap`
→ parse (kr/gap/parse.py) to `Cascade`

`Cascade` is the central object: levels, state↔config (1-based coords), letter valuations (for guards), `move_config`, `compute_stay_leave_from` / `compute_enters_to_from`, `build_configuration_automaton`, `accepting_configs` (Spot scc_info).

## Reconstruction

- `reachability_operators.py`: guard helpers, full inductive implementation of the 5 reachability formulas (strong/weak, solid/dashed, >0) with recursion to base, memo + early simplify, TRACE (KR_TRACE=1). (All 1L special case code deleted; pure paper for all depths.)
- `fin_c` implements Lemma 7 (Fin(C) via unconditional reach + >0 return).
- `reachability.py`: `reconstruct_ltl_1level_buchi` (public entry; name retained for compat) delegates to `reconstruct_ltl_paper_style` — the paper assembly using reach/fin_c + good Muller sets (from Spot) + DNF of ¬Fin/Fin conjunctions.
- 1L cases often produce simple output; multi-level use the generalized operators (may be large or partial until formula details polished).

## Usage

```python
from kr import decompose_aut, reconstruct_ltl_1level_buchi
import spot

aut = spot.formula("Fa").translate()
casc = decompose_aut(aut)
print(casc)                 # summary + levels
print(casc.state_to_config)
print(reconstruct_ltl_1level_buchi(casc))
```

See also `reconstruct_ltl_paper_style`, the reach_*/fin_c operators, and `generate_gap_script` / `extract_generators` for inspection.

## Dependencies

- `gap` on $PATH (GAP 4.12+).
- SgpDec loadable in GAP (`LoadPackage("SgpDec")`).

Run `./kr/install.sh` once for the SgpDec package (user-local under ~/.gap/pkg).

## Verification

`kr/testing/`:
- `test_kr_basic.py` — direct path + I/O + equiv + counters (argv supported).
- `test_kr_reconstruct.py` — isolated per-case decomp + reconstruct + Spot equiv.
- `diag_stability.py` — repeated decomp on multi-level cases.

All use subprocess isolation.

## Files

(See kr/STATUS.md for gaps; algorithm.md for the spec.)

This is PoC/experimental. Limited to small |AP| (explicit 2^|AP|). Formulas follow paper size bounds (large in worst case). Sinks from Spot completion are ordinary states.

The generated GAP scripts are deterministic and self-contained.