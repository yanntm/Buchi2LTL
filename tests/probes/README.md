# tests/probes/ — module probes

Per-module unit tests and POC probes for the `aut2ltl/` sources. Unlike
`aut2ltl_survey`, these are **dev-only and never installed** — they run against
the live source tree, including modules not yet declared/exported.

## Run them from the repo root, as modules

    python -m tests.probes.bls.test_kr_r4_audit
    python -m tests.probes.heur.test_fuse2

Running from the root puts the working tree on `sys.path`, so `import aut2ltl`
resolves to the live sources (no `pip install` needed) and sibling `tests.*`
corpora import normally. **Do not** run a probe by file path
(`python tests/probes/.../x.py`) — that puts only the script's own dir on the
path and the imports fail. There is intentionally **no** `sys.path` bootstrap
in any probe; the runner convention above replaces it.

## Layout

One subfolder per module under test (`bls/`, `daisy2/`, `language/`, `partscc/`,
`sccdecomp/`, …), plus a few flat `test_*.py` at this level for the
portfolio/contract floor. `smoke/` is a throwaway scratchpad for short-lived
probes (its run artifacts are gitignored).

## Gate

The correctness gate that must pass before committing engine changes:

    python -m tests.probes.bls.test_kr_r4_audit     # must report CLEAN
