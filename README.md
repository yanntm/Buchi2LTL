# aut2ltl

Translation of ω-automata to Linear Temporal Logic. The project pairs two
engines, composed by a portfolio that picks the winning method at each node:

* **`aut2ltl.kr`** — the *systematic* algebraic construction: Krohn-Rhodes
  holonomy cascade decomposition (SgpDec + GAP) following Boker, Lehtinen &
  Sickert, *"On the Translation of Automata to Linear Temporal Logic"*
  (FoSSaCS 2022) — no pattern matching on automaton shape. To our knowledge the
  first practical implementation of that construction.
* **`aut2ltl.sl`** — the *heuristic* engine: self-loop backward labeling, exact
  on the very-weak fragment and declining elsewhere, plus the f2 / tN SCC
  rescue heuristics (verify-before-use).

Both are language-faithful-or-decline, so the portfolio can compose them
soundly. On the Manna-Pnueli class ladder the combined path is a clean sweep
(every case verified equivalent). See `aut2ltl/kr/STATUS.md`.

## Layout

```
aut2ltl/                  the root package (layering: floor -> engines -> portfolio -> cli)
  contract.py            ReconResult + Translator (the contract floor)
  __main__.py            the portfolio front end:  python3 -m aut2ltl  (console: aut2ltl)
  cli.py                 legacy sl-engine demo:  python3 -m aut2ltl.cli
  kr/                    pure cascade FoSSaCS engine (cascade, reachability,
                         fin, acceptance_dispatch, gap_bridge, simplify/, ...)
  sl/                    heuristic engine (backward labeling + f2/tN heuristics)
  portfolio/             combinators: decompose_recombine, heuristic_gate, sl_driven
tests/
  kr/                    cascade-engine harnesses (gates: test_kr_r4_audit, survey_mp_cascade)
  sl/                    heuristic-engine debug/search scripts
  fixtures/             curated formula + HOA fixtures
  eval_roundtrip.py      batch round-trip evaluation harness
paper/                   construction reference + ground-truth paper text
```

## Quick start

```bash
# The front end: an LTL formula or a HOA file in, an equivalent LTL formula out.
python3 -m aut2ltl 'GFa & GFb'          # (or the `aut2ltl` console script)
python3 -m aut2ltl model.hoa            # HOA file (auto-detected; --ltl/--hoa force)
python3 -m aut2ltl 'F(a & X b)' -q | ltlfilt --simplify   # quiet: formula only

# Cite the techniques that may participate (cited order = priority, NO fallback):
python3 -m aut2ltl 'FG a' --use bls          # pure BLS-from-Muller
python3 -m aut2ltl 'FG a' --use buchi        # Buchi leaf only -> DECLINES (exit 1)
python3 -m aut2ltl 'FG a' --use buchi,cobuchi   # ladder: buchi declines, cobuchi wins

# Output: verbose report (technique, DAG/tree sizes, build time) on stderr by
# default; -q silences it. The formula is a hash-consed DAG — the flat string can
# explode, so it is gated (--flatten-limit), or dump the DAG itself:
python3 -m aut2ltl 'GFa & GFb' --dag | dot -Tpng -o dag.png

python3 -m aut2ltl --list-techniques     # the --use vocabulary
python3 -m aut2ltl --list-options        # every -O key, its default and doc
python3 -m aut2ltl --help

# Legacy sl-engine demo (original vs recovered LTL, technique, equivalence):
python3 -m aut2ltl.cli
```

Menu for `--use`: producers `acc weak buchi cobuchi bls sl` (ladder rungs, tried
in cited order) and wrappers `sl_driven decompose` (wrap the ladder). Omit `--use`
for the best default portfolio. Any declared option is overridable with
`-O key=value` (e.g. `-O kr.fuse_letters=0`).

```python
# Recommended top-level entry: automaton in, LTL formula DAG + technique out.
import spot
from aut2ltl.portfolio import reconstruct_decomposed

aut = spot.formula("GFa & GFb").translate()
res = reconstruct_decomposed(aut)          # ReconResult
print(res.formula, res.technique_str())    # formula DAG, e.g. "and2+sl"

# The pure cascade engine, per-automaton:
from aut2ltl.kr import decompose_aut, reconstruct_bls
casc = decompose_aut(spot.formula("Fa").translate())
print(reconstruct_bls(casc))
```

The reconstruction result is a `ReconResult` (`aut2ltl.contract`): `.formula`
(a hash-consed `spot.formula` DAG) or `.status == DECLINED`, plus `.technique`
(the set of methods that contributed).

## Dependencies

Runtime deps are NOT pip-installable; install them at system level:

* **Spot** (the `spot` and `buddy` Python bindings) — both engines.
* **GAP 4.12+** with the **SgpDec** package — the `kr` cascade engine only.
  Run `aut2ltl/kr/install.sh` once (user-local under `~/.gap/pkg`).

`pyproject.toml` carries the package metadata (`pip install -e .` installs the
`aut2ltl` package itself, not the external tools above).

## Evaluation harness

`tests/eval_roundtrip.py` batch-tests reconstruction over curated and random
formulas:

```bash
python3 tests/eval_roundtrip.py --samples --no-random -o stable.csv
python3 tests/eval_roundtrip.py -n 200 --seed 42 --aps 3 -o results.csv
```

Curated fixtures live in `tests/fixtures/` (`formulas.py`, `f2_successes.py`,
`terminal_2scc_labeled.py`, sample HOAs). See `--help` for all options.

## More

* `aut2ltl/kr/README.md` — kr engine doc map, pipeline, module map, testing tools.
* `aut2ltl/kr/STATUS.md` / `aut2ltl/kr/TODO.md` — current state / work items
  (incl. the P-ARCH reorganization campaign).
* `paper/automata-to-ltl-construction.md` — the construction reference;
  `paper/Automata2LTL.txt` — ground-truth paper text.
