# Witness log

A running lab log of non-LTL **witness** extraction experiments — the raw material
of the eventual "field guide" / definability atlas (`non_ltl_certificates.md` §6).
Each entry records what was run, on what, the witnesses produced, and how to
reproduce.

Design and code map: `research_notes/non_ltl_certificates.md` (§3 the object, §4
extraction, §10 where the code lives). The extractor is
`aut2ltl/bls/definability/witness/` — `extract_witness(lang, complete=…)` returns a
`Witness(p, v, factor, u, x_*)`: `v` is the period word and `p > 1` the period (from
a GAP group H-class + factorization); with `complete=True`, `u` reaches a state on
the `v`-orbit and `x` is a phase-discriminating lasso.

A witness `(u, v, x, p)` is a counting family: membership of `u·vⁿ·x` flips with
`n mod p`. It demonstrates that the language counts modulo `p`, which counter-free
LTL cannot express — i.e. why the language is not LTL-definable.

## How to reproduce

All from the repo root; GAP-bearing, small automata, fast.

One HOA in, witness out (single-input probe; verifies the toggle on the input
automaton):

    python3 -m tests.probes.witness.witness_on_hoa <file.hoa>

Unit test (counter example `parity_a` + LTL control `GFa` + stage-2 completion):

    python3 -m tests.probes.witness.test_witness

## 2026-06-25 — first witnesses on real corpus inputs (kinska counting, 1 AP)

Stage-2 family completion `(u, v, x, p)` brought up. Smoke on four kinska examples
known NOT_LTL and decided fast (~0.62 s in the reference survey), taken from
`samples/benchmark/inputs/kinska/`. Each synthesised family was verified to toggle
`u·vⁿ·x` membership on the **input** automaton (`n = 0…2p`).

| example                | states | p | v | u | x          | u·vⁿ·x |
|------------------------|--------|---|---|---|------------|--------|
| counting_buchi_1ap_01  | 2      | 2 | a | ε | !a; (a)ᵒ   | 10101  |
| counting_buchi_1ap_02  | 2      | 2 | a | ε | !a; (a)ᵒ   | 10101  |
| counting_buchi_1ap_05  | 3      | 2 | a | a | a; (!a)ᵒ   | 10101  |
| counting_buchi_1ap_08  | 3      | 2 | a | ε | (!a)ᵒ      | 10101  |

Reproduce one:

    python3 -m tests.probes.witness.witness_on_hoa \
      samples/benchmark/inputs/kinska/counting-1ap-counting_buchi_1ap_01.hoa

Observations:

- All four are mod-2 (parity of `a`): `p = 2`, `v = a` — as expected, one AP can
  essentially only count mod 2 (`p = 2` dominates, §6). The families differ in
  `u`/`x` with the automaton's shape but witness the same parity obstruction.
- Synthesised `u`/`x` are correct but not minimal (e.g. `_05`'s `u = a`); minimality
  is the §6 optimisation, not correctness.
- No `p ≥ 3` here, so the §4 GAP right-action order is **not** yet pinned (a 2-cycle
  equals its inverse). Next: a `p ≥ 3` counter — higher-AP counting, or a mod-3
  fixture — to pin the order, then minimisation, then the periodicity-proof tier.
