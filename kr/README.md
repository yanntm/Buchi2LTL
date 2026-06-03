# kr/ — Krohn-Rhodes / Holonomy Cascade Path (experimental)

This sub-tree contains the first steps toward an algebraic Büchi (HOA) → LTL translation using Krohn-Rhodes holonomy decomposition (via the SgpDec GAP package), following the approach in:

Udi Boker, Karoliina Lehtinen, Salomon Sickert.  
"On the Translation of Automata to Linear Temporal Logic". FoSSaCS 2022.

See the top-level README for overall project context. This is separate from the heuristic reconstruction in `buchi2ltl/`.

## Current Status (PoC / first milestone + Phase A/B start)

We have a working automated pipeline:

Spot deterministic automaton  
→ extract concrete generators (one per 2^|AP| letter)  
→ generate self-contained GAP script using SgpDec  
→ run via `gap`  
→ parse into `Cascade` (num_levels, per-level sizes, state → configuration mapping)

**Phase A complete**: Cascade now carries letter valuations, move_config(), build_config_transitions(), build_configuration_automaton(), and basic accepting config lift. The "configuration automaton" (states = appeared configs, labeled by valuations) is the object for the reachability logic.

**Phase B started**: 1-level reachability operators (base cases for reset components) in `reachability.py`, with `build_1level_reachability` etc. Tested on small examples including cases the old heuristic rejects (e.g. G(p → (q U r))).

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
from kr import decompose_aut
import spot

aut = spot.formula("Xa").translate("Buchi", "Deterministic")
casc = decompose_aut(aut)
print(casc)                    # summary
print(casc.state_to_config)    # the mapping you will need for LTL synthesis
print(casc.levels)             # sizes + kinds
```

You can also inspect the exact GAP script that was executed:

```python
from kr.gap_bridge import generate_gap_script
from kr.extract import extract_generators

gens, masks, valuations = extract_generators(aut)
script = generate_gap_script(gens)
print(script)   # or write to .gap file and inspect/run manually
```

Example generated scripts for the simple cases below live in `kr/examples/generated/`.

## Simple Examples (Xa, Fa, GFa, ...)

See `kr/examples/spot_det.py` and the generated/ .gap files.

Typical output (after `./kr/install.sh`):

(Results from actual run on this machine with GAP 4.15.1 + SgpDec 1.2.0.)

For "Xa":
- 3 states, 1 AP → 2 levels of size 2
- state_to_config: {0: (1, 1), 1: (1, 2), 2: (2, 1)}

For "Fa":
- 2 states, 1 AP → 1 level of size 2
- state_to_config: {0: (1,), 1: (2,) }

For "G(p -> X q)":
- 2 states, 2 APs → 1 level of size 2

Trivial 1-state cases (GFa etc.) correctly produce degenerate/empty cascades (expected; the language is simple enough that no interesting decomposition is needed).

The generated GAP scripts are fully self-contained (LoadPackage + the exact gens + the extraction Prints we need). They are deterministic given the input generators.

## Files of interest

- `install.sh` — convenience setup (run it; see its comments).
- `gap_bridge.py` — the script generator + runner + parser.
- `extract.py` — Spot aut → list of image lists (only for deterministic auts).
- `cascade.py` — the `Cascade` dataclass.
- `examples/generated/*.gap` — concrete generated scripts from the simple test cases (inspect these to see "what the GAP looks like").
- `examples/synthetic.py`, `examples/spot_det.py` — runnable demos.

This is still very much a proof-of-concept. The interesting (and large) next piece is transcribing the LTL reachability formulas from the Boker et al. paper on top of these cascades.
