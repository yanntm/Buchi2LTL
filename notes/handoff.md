# Handoff — non-LTL phase 3, end of the 2026-07-01/02 session

> Untracked scratch (the successor to `witness3.md`, which holds the full theory
> record). Read STATUS.md first as always; this file is the fast lane into where the
> last session stopped. Everything below is committed on `master`; the last PUSHED
> commit is `8bbac0a0` — **~20 commits since are local only, push pending**.

## What landed this session (all tested, fixture battery green)

Phase-3 fixes 1–4 plus plan items 1–2, docs-first throughout:

1. **Fail-safe gate** (`bls/definability/gate.py`): absorbing NOT_LTL only on a
   family replayed in-process; spurious group / unrunnable oracle
   (`definable=None`) ⇒ non-absorbing decline, cascade fenced, other arms free.
2. **Two witness shapes**: linear `u·vⁿ·x` + ω-power `u·(vⁿ·y)^ω`
   (`witness/{support,linear,enriched,omega}.py`, `Witness.y`,
   `verifier.verify_omega`). Exhaustive completion: all cycles ≥ 2 × all phase
   pairs; enriched-monoid candidates with index absorption (`ŷ = vᵃ·y`).
3. **Boundary revalidation**: a NOT_LTL crossing a language boundary is replayed
   or degraded. Decompose: through the PARTS (`revalidated_by_parts` — the
   connective of part memberships IS host membership; no parent product). Peels:
   daisy petal-drop and daisystardet exact reaching word (BDD-only local
   exactness, no replay); daisy2 (heuristic, per user: minimal effort) keeps the
   `revalidated` replay.
4. **Reseed recovery** (`witness/reseed.py`, hook-injected into the decompose
   brick by acceptance/scc/strength): a crossed verdict whose family fails the
   parts replay re-completes on the host from the child's `v` — **no GAP**.

Key fixtures (`samples/fixtures/hoa/definability/`): `gf_aa_parity` (spurious
group, was a live conclusive false reject, now declines→daisy2 answers LTL);
`evenblocks_nonltl` (prefix-independent genuine non-LTL — certified end-to-end
via reseeded ω-power family `p=2 u=[] v=[a] y=[a; !a]`); `gf_aa`, `sixap`.
Probes: `tests/probes/{gate_failsafe,omega_power_family,det_generic_form}.py`.

## Immediate next-session chores (before new work)

- **Run the validation survey** on the final state (`python3 -m survey --folder
  samples/validation` → must end SUCCESS; the two intermediate states each passed
  83/83 TRUE, the reseed-final state only passed the 5-fixture battery).
- **Clean genaut rerun**: `genaut/corpus/2state1ap1acc` (929 inputs; the old
  committed run has 122 NOT_LTL / 46 FAIL — ALL incomplete witnesses; e.g.
  `_00332` is provably LTL (`!a & GF(!a & X!a)`), a real false reject). The
  before/after on those rows is the headline measurement of the whole phase.
  The 2026-07-01 background rerun was DISCARDED (source edits landed mid-run —
  never edit .py during a live survey; .md is safe).
- Kinska scan + reference CSV refreshes (NOT_LTL technique cells now say `gate`;
  some verdicts may have become declines) — `results/README.md` procedure.
- **Push** (user authorizes per push, always ask).

## Open fronts (TODO.md "phase 3 remaining", user-triaged)

- **Item 3, cascade self-fence** (user: yes, "especially if doable without much
  more than better interaction with GAP"): decline on a group component inside
  the holonomy parse instead of misreading it as a reset. Makes bls sound on ANY
  form; closes the generic-vs-sbacc gap (gate certifies `det_generic_minimal`,
  cascade consumes `det_parity_sbacc` — different forms!). Docs-first in bls;
  user wants eyes on the component-classification story before code.
- **Item 4, Route B** (counter-free sibling search — definitive "is LTL" for the
  abstain zone): user says harder, "maybe a new research_notes/" — write the
  design note there, not code.
- daisy2 is a heuristic the user dislikes — don't invest; he will rework the
  peeler algorithm.md files himself ("a bit messy", his words).

## Working-style notes learned this session (beyond CLAUDE.md)

- Docs (algorithm.md/README) BEFORE code — "implem transcribes the pure idea".
- Never rewrite git history (now in CLAUDE.md); backticks in `-m` get shell-eaten
  — use `-F` with a quoted heredoc.
- No GAP / determinization on composed (whole) languages in the boundary
  machinery — parts queries and BDD restrictions only (the reseed's host det
  form is the accepted exception; it is cached on the Language).
- Don't read raw CSVs (token budget) — grep a few lines; prefer "rerun the
  survey and diff" over row archaeology.
- Fixtures for every finding, grouped in `samples/fixtures/hoa/definability/`;
  scratch notes at root progress to research_notes/ or the HISTORY sink when
  resolved — they are snapshots, not maintained docs.

## Theory quick-index (full record in `witness3.md`)

- `TM aperiodic ⟹ LTL` holds via Thomas 1979 (counter-free det Muller), NOT via
  the quotient argument (false on ω — acceptance reads marks along the run).
- Minimality rescues nothing: `GF(a ∧ Xa)` has two minimal 2-state forms, one
  with Z2 (residual-equal ≠ mergeable; minimal ≠ canonical).
- Linear families are provably blind on prefix-independent languages; Arnold's
  two context shapes ⟹ {linear, ω-power} is jointly complete.
- The cascade's precondition is a counter-free FORM, not language: even a proven
  "is LTL" doesn't license building from a groupy form (→ items 3 and 4).
