# aut2ltl.bls — cascade engine (automaton → LTL)

`kr` translates a deterministic ω-automaton into an equivalent LTL formula via
the Krohn–Rhodes / holonomy reset cascade, following the construction of Boker,
Lehtinen & Sickert (FoSSaCS 2022). It is algebraic and systematic — no
pattern-matching on the automaton's shape — and produces a hash-consed
`spot.formula` DAG (never serialized internally).

## Architecture

Translation is a family of **`CascadeTranslator` members** composed into a chain.

- **Contract** (`aut2ltl/contract.py`, the floor): `LTLResult` (a formula
  DAG + technique set + OK/DECLINED status) and the `CascadeTranslator` protocol —
  `holder → LTLResult`, with a fixed `name`. A member is a small class
  (singleton instance) that is **self-gating**: it inspects the cascade and
  either returns a language-faithful result or DECLINES; it stamps its own
  `name` into the technique.

- **Members** (`holder → LTLResult`):
  - `acc.py` — `Acc` / `acc`: the bounded ("X-ladder") fragment, by direct
    bounded unroll over a ⊤/⊥ oracle on the input automaton. Orthogonal to the
    reach machinery; declines on any recurrent config.
  - `bls.py` — `Bls` / `bls`: the general case (the full Muller-DNF
    construction). The chain's fallback; accepts every LTL-expressible cascade.
  - `buchi.py` / `cobuchi.py` / `weak.py` — the direct hierarchy-class members
    `buchi` (`⋁¬Fin`), `cobuchi` (`⋀Fin`), `weak` (reach-only), each self-gating
    on its class (`is_{buchi,cobuchi,weak}_cascade`).

- **Composition** (`aut2ltl/combinators.py`): `first_success([...])` — try the
  members in order, take the first OK, else DECLINE. The acceptance-dispatch
  chain `acc → weak → buchi → cobuchi → bls` is assembled by
  `make_hierarchy_class` (`hierarchy_class.py`); per-member gates are read from
  the injected `Options` (`kr.dispatch.*`, env bridge `KR_DISPATCH_*`). The CLI
  exposes the whole chain as the `str` technique.

- **Support** (build a formula, *not* translators):
  - `reachability_operators.py` + `fin.py` — the five inductive reachability
    formulas and `Fin(C)` (Lemma 7): the mutually-recursive core.
  - `muller.py` — `assemble_muller_dnf`: the general Δ₂ Muller-DNF over the good
    config sets. `Bls` wraps it.
  - LTL utilities moved OUT of kr to the floor package `aut2ltl/ltl/` (shared by
    kr/sl/portfolio): `ltl/builders.py` (hash-consed formula builders, the simplify
    hook, DAG→text `_str_f`), `ltl/simplify/` (own simplify/fold passes), and
    `ltl/bdd_utils.py` (buddy-BDD letter classification, used by `kr/extract.py`).

## Pipeline

```
spot automaton
  │  decompose_aut  (kr.gap)
  ▼
normalize → deterministic, complete, minimized, state-based-acceptance parity
  → extract one generator per concrete letter (extract.py)
  → GAP / SgpDec holonomy decomposition, parsed back        (kr.gap — see its README)
  ▼
Cascade                              (cascade/model.py + cascade/config_graph.py)
  │  the dispatch chain of CascadeTranslator members         (hierarchy_class.py)
  ▼
LTLResult  (hash-consed spot.formula DAG + winning technique)
```

`decompose_aut` and the GAP/SgpDec bridge live in the **`kr.gap`** subpackage
(its own README). `cascade/model.py` is the data model (levels, state↔config,
letter valuations, `move_config`); `cascade/config_graph.py` does the
config-automaton analysis (reachable/accepting configs, good Muller sets).

## Usage

```python
import spot
from aut2ltl.bls import decompose_aut, reconstruct_bls

casc = decompose_aut(spot.formula("G(p -> (q U r))").translate())
phi = reconstruct_bls(casc)            # the dispatch chain, formula DAG out
print(phi)
```

The recommended top-level entry is the portfolio front end
`aut2ltl.portfolio.reconstruct_decomposed(Language.of(aut))` (a `Language` in, an
`LTLResult` out), which composes `kr` with the `sl` heuristic gate.

## Dependencies

GAP (≥ 4.12) with the SgpDec package on `PATH`. Install once:
`./aut2ltl/bls/gap/install.sh` (user-local under `~/.gap/pkg`).

## Docs & tests

- `paper/Automata2LTL.txt` — ground truth for any formula-fidelity question.
- `paper/automata-to-ltl-construction.md` — the construction reference.
- `../../docs/algorithm.md` — scope/policy and module mapping.
- `STATUS.md` / `TODO.md` — current state / work items.
- `../../docs/dag_folding.md` — the size-explosion analysis (open research).
- Tests: `tests/kr/` holds the cascade unit tests + debug tools
  (`test_kr_r4_audit.py` is the structural gate); the correctness gate is the
  front-end survey `tests/survey.py` (ends SUCCESS/FAIL).
