# tests/probes/bls/

Probes and unit tests for the `aut2ltl/bls` cascade engine. The folder is
structured like the source it exercises (e.g. `simplify/` for the simplify
pipeline) — look around; each probe is self-describing.

For the running convention and discipline (placed scripts, run from the repo root
as `python3 -m tests.probes.bls.<probe>`), see [`../README.md`](../README.md) and
the top-level [`tests/README.md`](../../README.md).

One bls-specific note: Spot/buddy can segfault on accumulated state (rc 139), so
isolate each case in its own subprocess — follow the existing scripts.
