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
(every case verified equivalent).

## Command-line tool

`python3 -m aut2ltl` (console script `aut2ltl`) is the front end: an LTL formula
or a HOA automaton file in, an equivalent LTL formula out.

```bash
python3 -m aut2ltl 'GFa & GFb'          # an LTL formula in
python3 -m aut2ltl model.hoa            # a HOA file (auto-detected; --ltl/--hoa force)
python3 -m aut2ltl 'F(a & X b)' -q | ltlfilt --simplify   # quiet: formula only on stdout

# Cite the techniques that may participate (cited order = priority, NO fallback):
python3 -m aut2ltl 'FG a' --use bls          # pure BLS-from-Muller
python3 -m aut2ltl 'FG a' --use str          # the integrated kr cascade
python3 -m aut2ltl 'GFa & GFb' --use decompose,str   # cascade under strength decomposition
python3 -m aut2ltl 'FG a' --use buchi        # Buchi leaf only -> DECLINES (exit 1)

# The verbose report (technique, DAG/temporals/tree sizes, build time) goes to
# stderr by default; -q silences it. The formula is a hash-consed DAG — the flat
# string can explode, so it is size-gated (--flatten-limit), or dump the DAG:
python3 -m aut2ltl 'GFa & GFb' --dag | dot -Tpng -o dag.png

python3 -m aut2ltl --list-techniques     # the --use vocabulary
python3 -m aut2ltl --list-options        # every -O key, its default and doc
python3 -m aut2ltl --help
```

Menu for `--use`: producers `acc weak buchi cobuchi bls str sl` (ladder rungs,
tried in cited order; `str` is the integrated default cascade) and wrappers
`sl_driven decompose` (wrap the ladder). Omit `--use` for the best default
portfolio. Any declared option is overridable with `-O key=value` (e.g.
`-O kr.fuse_letters=0`).

```python
# Programmatic entry: a Language in, an LTLFormulaResult out.
import spot
from aut2ltl.language import Language
from aut2ltl.portfolio import reconstruct_decomposed

aut = spot.formula("GFa & GFb").translate()
res = reconstruct_decomposed(Language.of(aut))   # LTLFormulaResult
print(res.formula, res.technique_str())          # formula DAG, e.g. "and2+sl"
```

The result is an `LTLFormulaResult` (`aut2ltl.contract`): `.formula` (a
hash-consed `spot.formula` DAG) or `.declined`, plus `.technique` (the methods
that contributed). A `Language` (`aut2ltl.language`) wraps any input
(`Language.of(aut)` / `Language.of_ltl(formula)`) as lazily-cached,
language-equivalent automaton views.

## Layout

```
aut2ltl/                  the root package (layering: floor -> engines -> portfolio -> cli)
  contract.py            LTLFormulaResult + Translator (the contract floor)
  language.py            Language: lazy language-equivalent automaton views
  __main__.py            the portfolio front end:  python3 -m aut2ltl  (console: aut2ltl)
  kr/                    pure cascade FoSSaCS engine (cascade/, reachability,
                         fin, acceptance_dispatch, gap/, simplify/, ...)
  sl/                    heuristic engine (backward labeling + f2/tN heuristics)
  portfolio/             combinators: build, decompose, heuristic_gate, sl_driven
  ltl/                   engine-agnostic helpers: metrics, printers, simplify/
tests/
  survey.py              front-end survey over a corpus (the correctness gate)
  survey_formulas.py     the curated, annotated corpus
  survey_sweep.sh        sweep the front end across --use configurations
  survey_diff.py         quantitative diff of two survey CSVs
  kr/                    cascade-engine unit tests + debug tools (test_kr_r4_audit, ...)
  sl/                    heuristic-engine fixture generators (find_*)
  fixtures/              curated formula + HOA fixtures
docs/                     algorithm.md, dag_folding.md (research notes), HISTORY.md
paper/                    construction reference + ground-truth paper text
```

## Dependencies

Runtime deps are NOT pip-installable; install them at system level:

* **Spot** (the `spot` and `buddy` Python bindings) — both engines.
* **GAP 4.12+** with the **SgpDec** package — the `kr` cascade engine only.
  Run `aut2ltl/kr/install.sh` once (user-local under `~/.gap/pkg`).

`pyproject.toml` carries the package metadata (`pip install -e .` installs the
`aut2ltl` package itself, not the external tools above).

## Testing

The front-end survey is the correctness gate — it reconstructs a corpus through
the actual CLI and verifies each result with Spot:

```bash
python3 tests/survey.py                    # the curated corpus; ends SUCCESS / FAIL
python3 tests/survey.py "G(p -> (q U r))"   # a single formula
python3 tests/survey_sweep.sh tests/logs/reference   # sweep all --use configs
python3 tests/survey_diff.py OLD.csv NEW.csv          # before/after a change
python3 tests/kr/test_kr_r4_audit.py        # structural audit gate (must stay CLEAN)
```

`SUCCESS`/`FAIL` is definite: `FAIL` means a *verified non-equivalent* formula
was produced. Spot timeouts / size explosions / >32-acceptance-set walls are
reported as their own categories, never as failures — a DAG we built that Spot
cannot verify is not our fault. The committed release baseline lives in
`tests/logs/reference/`.

## More

* `aut2ltl/kr/README.md` — kr engine doc map, pipeline, module map, testing tools.
* `aut2ltl/kr/STATUS.md` / `aut2ltl/kr/TODO.md` — engine state / work items.
* `STATUS.md` / `TODO.md` — project-level snapshot / open items.
* `docs/algorithm.md` — the construction's scope and module mapping.
* `docs/dag_folding.md` — the size-explosion analysis (open research direction).
* `docs/HISTORY.md` — the dated construction log.
* `paper/automata-to-ltl-construction.md` — the construction reference;
  `paper/Automata2LTL.txt` — ground-truth paper text.

## License

Distributed under the **GNU General Public License v3.0** (see `LICENSE`).

© 2026 Yann Thierry-Mieg, LIP6, Sorbonne Université, CNRS.
