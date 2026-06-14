# kr/testing/

Development and verification scripts for the kr/ algebraic path.
The script-by-script overview lives in `kr/README.md` ("Verification" section);
this file only records the ground rules.

## Rules

- Run from the project root; scripts insert the root on sys.path themselves.
- Placed scripts only: no /tmp artifacts, no `python -c` one-liners.
- Subprocess isolation per case (Spot/buddy can segfault on state accumulation;
  rc 139 = segv) — use the existing scripts as templates.
- Use timeouts (5–45s per case).
- One-shot probes (single-question tools): commit the script, record the
  finding in `kr/STATUS.md`, then delete it — git history keeps the tool.
- Run logs are never committed; the exception is `logs/` (curated baseline
  size censuses kept as before/after references for fold work).

## Gate before committing operator/assembly changes

    python3 kr/testing/test_kr_r4_audit.py        # must report CLEAN
    python3 kr/testing/survey_mp_cascade.py        # previously-True must stay True

## Debug method (contradiction milking)

1. `survey_mp_cascade.py` — pick the smallest failing case (weakest MP class).
2. `trace_fin_semantics.py "<formula>"` — ground each fin_c sub-term against
   ground-truth automata; find the first diverging sub-term + witness word.
3. `ltl_diff.py "<A>" "<B>"` — containment direction + witness for any two formulas.
4. `test_kr_zoom.py "<formula>"` — full KR_TRACE=1 construction trace.
5. Fix against `paper/Automata2LTL.txt`, re-run the gate, commit (one file).
