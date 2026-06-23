# tests/probes/bls/

Probes and unit tests for the `aut2ltl/bls` cascade engine. The folder is
structured like the source it exercises (e.g. `simplify/` for the simplify
pipeline) — look around; each probe is self-describing.

For the running convention and discipline (placed scripts, run from the repo root
as `python3 -m tests.probes.bls.<probe>`, and the budget/isolation harness to
reuse instead of hand-rolling subprocess handling), see
[`../README.md`](../README.md) and the top-level [`tests/README.md`](../../README.md).
