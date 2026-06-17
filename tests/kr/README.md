# tests/kr/

Development and verification scripts for the kr/ algebraic path.
The script-by-script overview lives in `aut2ltl/bls/STATUS.md` ("Tooling for
targeted work"); this file only records the ground rules.

## Rules

- Run from the project root; scripts insert the root on sys.path themselves.
- Placed scripts only: no /tmp artifacts, no `python -c` one-liners.
- Subprocess isolation per case (Spot/buddy can segfault on state accumulation;
  rc 139 = segv) — use the existing scripts as templates.
- Use timeouts (5–45s per case).
- One-shot probes (single-question tools): commit the script, record the
  finding in `docs/HISTORY.md`, then delete it — git history keeps the tool.
- Run logs are never committed; the exception is the curated release baseline
  under `tests/logs/reference/` (the committed survey sweep).

## Gate before committing operator/assembly changes

    python3 tests/kr/test_kr_r4_audit.py     # must report CLEAN
    python3 tests/survey.py                  # must end SUCCESS (no verified non-equiv)

## Debug method (contradiction milking)

1. `tests/survey.py "<formula>"` — survey one case; check that it validates.
2. `trace_fin_semantics.py "<formula>"` — ground each fin_c sub-term against
   ground-truth automata; find the first diverging sub-term + witness word.
3. `ltl_diff.py "<A>" "<B>"` — containment direction + witness for any two formulas.
4. `test_kr_zoom.py "<formula>"` — full KR_TRACE=1 construction trace.
5. Fix against `paper/Automata2LTL.txt`, re-run the gate, commit (one file).
