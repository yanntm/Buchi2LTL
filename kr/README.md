# kr/ — Krohn-Rhodes / Holonomy Cascade Path (experimental)

This sub-tree contains the first steps toward an algebraic Büchi (HOA) → LTL translation using Krohn-Rhodes holonomy decomposition (via the SgpDec GAP package), following the approach in:

Udi Boker, Karoliina Lehtinen, Salomon Sickert.  
"On the Translation of Automata to Linear Temporal Logic". FoSSaCS 2022.

See the top-level README for overall project context. This is separate from the heuristic reconstruction in `buchi2ltl/`.

## Current Status (PoC + 1-level clean reconstruction)

We have a working automated pipeline:

Spot deterministic automaton  
→ extract concrete generators (one per 2^|AP| letter, with dead-trap completion for incomplete auts)  
→ generate self-contained GAP script using SgpDec  
→ run via `gap`  
→ parse into `Cascade` (num_levels, per-level sizes + kinds, state → configuration mapping)

**Decomposition + Configuration Automaton (Phase A)**: Fully general. `Cascade` carries letter valuations (for LTL guards), `move_config()`, `build_config_transitions()`, `build_configuration_automaton()`, and `accepting_configs()`. The configuration automaton is the foundation for reachability.

**Reachability + Clean Reconstruction (Phase B extended)**: 
- Generalized inductive 5 reachability formulas (paper Table 1 / Sec 4.2) in `reachability_operators.py`: `reach_strong`/`reach_weak` (Formulas 1/2), solid stay (3/4 with 4 cases + >0), dashed change (5). Base level 0 plain U; recursion on config len via new Cascade sub/Stay/Leave/Enter utils (compute_*_from using move_config). 1-level delegates to old optimized when top-level 1-casc for compat. `simplify_ltl` integrated.
- `reconstruct_ltl_1level_buchi` + `build_infinitely_often_accepting` now attempt multi (up to 2 levels; >2 fallback) using the generalized reach (no hard NotImpl). Safety short G(stay_g) for init-acc 1-level cases (Ga family).
- **TRACE support**: `KR_TRACE=1` (or set TRACE_ON) for detailed dev traces of the inductive construction (very helpful for cases like "a").
- Still "inf often" framing (not full Fin/acc/Muller assembly); formulas on multi often partial/degen until polish. "a" now fully recovered (see STATUS.md for diagnosis). Heuristic kept for comparison.
- Tested via `kr/testing/` (1-level equiv good; multi exercises new path; test_kr_basic.py for simple normal-path I/O).

**Multi-level / Full General**: Inductive K (5 formulas + recursion + partitions) landed and exercised on 2-level; 3+ limited for stability. Full Fin(C) (Lemma 7), acceptance lift/assembly, and class preservation remain (see kr/algorithm.md + STATUS.md). Clean path usable on some multi but output not yet always correct/equiv.

We follow a "smaller files, one service per module" discipline (see `reachability_operators.py`, `bdd_utils.py` for stability, `gap/parse.py`, `kr/testing/` for verification harnesses).

See `kr/STATUS.md` for detailed roadmap/gaps and `kr/testing/README.md` + test scripts for verification.

Later work will complete the inductive multi-level case + acceptance encoding + top-level formula (per the Boker et al. roadmap).

## Dependencies (what must be on PATH / loadable)

- `gap` (the GAP computer algebra system executable) must be found on your `$PATH`.
  - On Fedora: `sudo dnf install gap gap-core gap-pkg-semigroups` (and friends) is usually sufficient for the base.
  - Other distros: equivalent `gap` / `gap-core` packages.

- The **SgpDec** package must be loadable inside GAP (`LoadPackage("SgpDec")` succeeds).

The easiest way to satisfy the second requirement is to run once:

    ./kr/install.sh

It will download (or git-clone) the current SgpDec release and place it under `~/.gap/pkg/sgpdec` (user-local, no root required for that step). It also does a basic verification.

We are still in PoC stage; there is no fancy multi-platform / container / CI setup yet.

## Usage

```python
from kr import decompose_aut, reconstruct_ltl_1level_buchi, reconstruct_ltl_1level_buchi_heuristic
import spot

aut = spot.formula("Fa").translate("Buchi", "Deterministic")
casc = decompose_aut(aut)
print(casc)                    # summary
print(casc.state_to_config)    # mapping for LTL synthesis
print(casc.levels)             # sizes + kinds

# Clean thin path (preferred for 1-level; uses K operators only)
print(reconstruct_ltl_1level_buchi(casc))

# Old ad-hoc version (for comparison)
print(reconstruct_ltl_1level_buchi_heuristic(casc))
```

You can also inspect the exact GAP script:

```python
from kr.gap_bridge import generate_gap_script
from kr.extract import extract_generators

gens, masks, valuations = extract_generators(aut)
script = generate_gap_script(gens)
print(script)
```

Parsing of GAP output is now in the focused `kr/gap/parse.py` service (re-exported from `gap_bridge` for compatibility).

Example generated scripts live in `kr/examples/generated/`.

## Simple Examples (Xa, Fa, GFa, ...)

See `kr/examples/spot_det.py`, `kr/examples/synthetic.py`, `kr/testing/test_kr_reconstruct.py`, and the generated/ .gap files.

Note: Adding a dead rejecting trap for incomplete auts (language-preserving) often increases state count and can produce additional trivial (size-1) levels in the cascade compared to older snapshots.

Typical current behavior (after `./kr/install.sh`):
- Trivial 1-state or simple safety cases often produce small/1-level cascades or degenerate results.
- 1-level cases like Fa now go through the clean K-operator path and produce simple equivalent formulas (e.g. `F(((!a) U (a & true)))`).
- Multi-level cases (common with dead trap) raise `NotImplemented` in the clean path and fall back to the heuristic.

The generated GAP scripts are fully self-contained. They are deterministic given the input generators.

See `kr/testing/` (and its README) for the verification harnesses we use to compare clean vs heuristic and confirm stability (subprocess isolation + repeated decomp on historically problematic cases like Xa).

## Files of interest

- `install.sh` — convenience setup for GAP + SgpDec.
- `gap_bridge.py` — orchestration, script generation, and execution. (Parser extracted to the focused service below for smaller files.)
- `gap/parse.py` + `gap/__init__.py` — focused parser service (structured GAP output → `Cascade`). Re-exported from `gap_bridge` for compatibility.
- `extract.py` — Spot aut → generators (with dead-trap completion for language correctness).
- `cascade.py` — `Cascade` dataclass + config automaton helpers (`build_configuration_automaton`, `move_config`, etc.).
- `reachability_operators.py` — 1-level K operators (`one_level_reach_strong`, `build_1level_reachability`, guard helpers, etc.) + 1-level projection helpers. The core "intelligence".
- `reachability.py` — thin high-level layer: `reconstruct_ltl_1level_buchi` (clean pure builder using the operators) + `_heuristic` (old ad-hoc for comparison) + `build_infinitely_often_accepting`.
- `bdd_utils.py` — stability helpers (precomputed buddy var maps to avoid sporadic segfaults during extraction).
- `examples/` + `testing/` — demos and verification harnesses (see `kr/testing/README.md` and `test_kr_reconstruct.py` / `diag_stability.py`).
- `examples/generated/*.gap` — inspectable generated scripts.

This remains experimental/PoC. The next major piece is the inductive multi-level K operators (per Boker et al.) + Fin/Inf/acceptance encoding on top of the clean 1-level foundation. See `kr/STATUS.md` for the detailed current state and gaps.
