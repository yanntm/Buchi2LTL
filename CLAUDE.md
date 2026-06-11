# BuchiToLTL — Working Notes for Claude

## Project layout
- `kr/` — pure algebraic Büchi→LTL via Krohn-Rhodes cascades (Boker–Lehtinen–Sickert FoSSaCS 2022). **Current focus.** No pattern matching allowed here.
- `buchi2ltl/` — separate heuristic path (f2/tN). Do not mix the two.
- `paper/Automata2LTL.pdf` (+ `.txt` extract) — the source paper.
- Authoritative progress docs: `kr/STATUS.md`, `kr/TODO.md`. Spec: `kr/algorithm.md`. Detailed pseudocode + R4 corrections: `kr/automata_to_LTL_reference.md`.

## Discipline (mandatory)
- One file per commit. No commit without explicit user approval.
- Update `kr/STATUS.md` + `kr/TODO.md` *before* committing a code change (separate doc commits are fine).
- Test BEFORE commit: run placed scripts under `timeout` (5–45s), at minimum:
  - `python3 kr/testing/test_kr_r4_audit.py` (must stay CLEAN)
  - `python3 kr/testing/test_kr_reconstruct.py a Fa "G(p | F q)"` (Fa/a equiv must stay True — regression guard)
- Only *placed* scripts under `kr/testing/` — no `/tmp`, no long `python -c` pastes.
- Subprocess isolation per test case (Spot/buddy can segfault on state accumulation; rc 139 = segv).

## Test-driven approach (current)
Small targeted cases per rule/formula-case, organized by Manna-Pnueli class (weakest first: safety → guarantee → obligation → recurrence → persistence → reactivity). Use `spot.mp_class(f)` for classification. Drive R4/Rws0 fixes with the smallest failing 2-level cascade cases.

## Useful env / tools
- `KR_TRACE=1` — detailed inductive construction traces in reachability_operators.
- `python3 kr/testing/test_kr_zoom.py "<formula>"` — full deep dive (aut, cascade, Muller, trace, equiv) on one formula.
- Spot equivalence: `spot.are_equivalent(aut1, aut2)`; translate with `f.translate("Buchi")`.
- GAP/SgpDec must be installed (see `kr/install.sh`); decomposition runs via subprocess.

## Current P0 (R4 / Rws / Rws0 correctness, paper pp. 11–12)
1. Rws0 line(2) "stay-forever" disjunct present, OR-ed with line(1).
2. Rws0 line(1) omits Rs0's unconditional "freely reach T'" conjunct.
3. Bad-predecessor/Leave avoids inside Rws0 use Rw (weak), not R.
4. Outer Rws case 4 (S=B=T) is exactly `(Rws0 ∨ τ) ∧ ¬β`.
5. R5 line(2) calls weak with swapped roles ((T,t,τ)→bad, (B,b,β)→target).

Audit (`test_kr_r4_audit.py`) reports CLEAN structurally; canary `G(p | F q)` equiv still False — behavioral work remains.
