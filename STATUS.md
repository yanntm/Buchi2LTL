# aut2ltl — Project Status

Project-level snapshot. For the **engine** state read `aut2ltl/bls/STATUS.md`
(the FoSSaCS'22 cascade core); for construction history read `docs/HISTORY.md`.

## What works

The FoSSaCS'22 automaton→LTL construction is implemented end-to-end and
semantically validated. The portfolio front end is the **`cake` recipe** (the
no-`--use` default since 2026-06-19): a **shy `best_of`** over the `best_daisy2`
incumbent (`Simplify(strength(acceptance(daisy_pair(core))), "hi")`, `core =
first(partscc, bls)` — the one cascade) and one CHEAP every-technique rich variant
(`Invariant ∘ Strength ∘ Scc ∘ Invariant ∘ Acc ∘ daisy_pair_inv`) that floors on
`partscc` only (no second cascade), displacing the incumbent only on a significant
form win. On the 373-case benchmark it is a Pareto step over `best_daisy2` (11 wins
−25…−41 %, 0 regressions, +1 answered, ≈same build); kinská-neutral.
`best_daisy2` (`--use best_daisy2`) remains the prior default — the daisy/daisy2 peel
pair (self-loop daisy, then the length-1 star `daisy2`, see
`aut2ltl/daisy2/algorithm.md`) flooring on the `bls` cascade. It sweeps the
Manna–Pnueli class ladder, every probed case verifying equiv=True; on the 373-case
benchmark it is sound (0 non-equivalent) and −3.6% DAG vs the prior `best`, even
turning one 3804-node unverifiable answer into a verified 16-node one. `--use best`
is the prior daisy-only assembly; `--use best_inv` adds the global-invariant layer
(benchmark-neutral here). daisy2 itself is still **gate-rescued** on the safety
half (a Spot equivalence gate; see its algorithm.md). Engine internals and the
size profile live in `aut2ltl/bls/STATUS.md`.

## Combinator algebra (2026-06-19)

The portfolio combinators are named into a small (almost-)algebra over
language-manipulators (Translators carrying *faithful-or-⊥*; **soundness is closed
under every operation**, so any writable recipe is sound by construction). See
[`COMBINATORS.md`](COMBINATORS.md) for the lens and law table. Two sorts: translators
and `Decorator`s (`aut2ltl/translator.py`). Operations: `first_success` (`⊕`) /
`best_of` (`⊞`) / `compose` (`∘`, `aut2ltl/compose.py`, unit `identity`) / `recurse`
(`fix`), plus the `∧/∨` combine (`aut2ltl/decomp/decompose.py`). The five recipes are
flat point-free `compose(...)` terms, and the three `decomp` decomposers
(strength/acceptance/scc) collapsed onto the one `decompose(split, connective, tag)` —
all behavior-preserving (survey unchanged at DAG=414). Scope fence: free named
combinators only — no DSL, no AST, no meta-level reflection. Open levers (TODO): the
`best_of` wiring recipe and `recurse` memoization.

## Front end (CLI)

`aut2ltl/__main__.py` (`python3 -m aut2ltl`, console script `aut2ltl`) is the
portfolio front end: an LTL formula or HOA file in, an equivalent LTL formula
out. `--use` cites the techniques that may participate (the producers `acc weak
buchi cobuchi muller bls`, where `muller` is the general Muller-DNF leaf and `bls`
the integrated cascade) or names a recipe (`best` / `best_daisy2` / `best_inv`);
omit it for the `best_daisy2` default.
`-O key=value` overrides any
declared option (`--list-options`/`--list-techniques` to discover). The verbose
report (technique, DAG/temporals/tree sizes, build time) goes to stderr (`-q`
silences); `--dag` dumps the formula DAG as graphviz dot; DECLINE ⇒ exit 1.

## Testing

The front-end survey is the correctness gate — it reconstructs a corpus through
the CLI and verifies each result with a Spot oracle (a test-only check, never a
client cost):

- `tests/survey.py` — corpus survey; per-formula CSV + a compact summary ending
  in `SUCCESS`/`FAIL`. `FAIL` = a verified non-equivalent formula (a definite
  wrong answer); spot timeouts / size explosions / >32-acc-set walls are their
  own categories, NOT failures (a DAG we built that Spot cannot verify is not
  our fault). The corpus is `tests/survey_formulas.py`.
- `tests/survey_sweep.sh` — the same survey across every `--use` configuration,
  one log each + a cross-config SUMMARY. `tests/survey_diff.py` diffs two CSVs.
  The committed release baseline is `tests/logs/reference/`.
- `tests/kr/test_kr_r4_audit.py` — structural audit gate (must stay CLEAN).
- `tests/benchmark/` — the portfolio evaluation **bench** (size, not a gate):
  A/B two portfolios over `inputs/` (the survey corpus + W/U/R chains + 105
  Kinská HOA), reusing the survey engine; `bench_sweep.sh` + `survey_diff.py`.
  Reference runs committed under `tests/benchmark/logs/reference/`.

## Layout

`aut2ltl/contract.py` (floor) + `aut2ltl/language.py` ← `aut2ltl/bls` (pure
cascade engine) + the (de)composition translators (`aut2ltl/daisy`,
`aut2ltl/partscc`, `aut2ltl/decomp`) ← `aut2ltl/portfolio` (combinators) ←
`aut2ltl/__main__`. Engine-agnostic helpers in `aut2ltl/ltl`. Tests under `tests/`
(`survey*`, `tests/kr`, `tests/heur`, `tests/fixtures`, `tests/benchmark`).
`aut2ltl/ltl/simplify` carries its own `algorithm.md` spec.
