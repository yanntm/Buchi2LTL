# Non-LTL phase 3 — the algebraic verdict is not decisive; the witness (both shapes) must be the authority

> Untracked working note, state of mind 2026-07-01. Lineage: `nonltl.md` (the one-way
> verdict) → `witness.md` (stage 2, replay-clean witnesses) → this. Fixtures and probes
> referenced here are committed; this note is the findings + plan.

## Theory findings (established this session, on paper + fixtures)

**F1 — the quotient argument in the docs is invalid; the positive direction survives
via a different theorem.** `tester/algorithm.md` / `nonltl.md` justify `TM aperiodic ⟹
LTL` by "same state action ⟹ interchangeable in every context ⟹ the syntactic
ω-semigroup `S` is a quotient of `TM`". False for ω-automata: acceptance reads the
states/transitions visited *along* the run, so two words with equal state maps but
different intermediate visits can be separated by an ω-power context (`x·u^ω` vs
`x·v^ω` with different inf-sets) — `S` can be strictly finer than `TM`. The conclusion
still holds, by Thomas (1979): a counter-free deterministic **Muller** automaton
recognizes a star-free language; Emerson–Lei acceptance depends only on the inf-set, so
it reduces to Muller. Doc fix pending (cite Thomas, drop the quotient sketch).

**F2 — minimization does NOT rescue the negative direction.** Two independent failures:
- *residual-equal ≠ mergeable*: ω-states are memory for the acceptance, not only the
  residual; prefix-independent languages are the extreme (every state of every
  automaton has residual exactly `L`, yet >1 state is needed).
- *minimal ≠ canonical*: `GF(a & Xa)` has two non-isomorphic minimum-size (2-state)
  deterministic Büchi automata — the last-letter form (aperiodic, `gf_aa.hoa`) and the
  run-parity form (Z2 transposition in TM, **`gf_aa_parity.hoa`**). Mechanism: the two
  mark different transition sets on every run but the verdicts agree in the limit —
  modular counts collapse to thresholds at infinity (`Σ⌊kᵢ/2⌋ = ∞ ⟺ kᵢ≥2 i.o.`).
  Nothing forces SAT-min to pick the aperiodic sibling.

**F3 — the linear witness shape is provably blind on prefix-independent languages.**
If `L` is prefix-independent then `u·vⁿ·x ∈ L ⟺ x ∈ L` — constant in `n` for *every*
`(u,v,x)`; equivalently all reachable states are residual-equal so `_distinguish` can
never separate any phase pair (widening to all pairs cannot help). Non-LTL
prefix-independent languages exist (**`evenblocks_nonltl.hoa`**: infinitely many `!a`
and eventually every `a`-block even). The complete system needs the second, **ω-power
shape** `u·(vⁿ·y)^ω` toggling with `n mod p`. This is not ad hoc: Arnold's syntactic
congruence for ω-languages tests exactly two context shapes — linear `x _ y·t^ω` and
ω-power `x(_ y)^ω` — so the two family shapes together are expressively complete for
exhibiting syntactic non-aperiodicity. Each `n` of the ω-power shape is still a lasso,
so membership replay extends with only a serialization change.

## Fixtures + observed behavior (logs: `logs/nonltl_fixtures/`)

**`gf_aa_parity.hoa`** (≡ `GF(a & Xa)`, verified by `survey.diff.diff_hoa`):
- Probe `tests/probes/det_generic_form.py` (real Language path):
  `det_generic_minimal()` keeps the swap intact; `label_ltl_definable` returns
  **`(definable=False, conclusive=True)`** — a live, conclusive-grade false verdict,
  cached on the Language. This is the spurious-group regression fixture `nonltl.md`
  asked for.
- The default recipe still answers `LTL: GF(a & Xa)` via daisy2 — `first_success`
  ordering means a gated rung is never consulted. **Ordering hides the defect** (by
  design we delay determinization outside `bls/`, but hidden it is): a `best_of` walk
  (observed once via `--use best`) consults the gated arm, and the absorbing false
  `NOT_LTL` **discards a correct formula already in hand**.
- The witness correctly does *not* complete (the two states are residual-equal) — so
  completed-witness-gated abstain fixes exactly this case, and daisy2 preserves
  completeness.

**`evenblocks_nonltl.hoa`** (genuinely non-LTL, prefix-independent):
- Probe `tests/probes/omega_power_family.py`: ω-power pattern `1010101` (the genuine
  mod-2 count), linear pattern `1111111` (blind — F3 made concrete).
- Default run: `NOT_LTL` (verdict correct) but with a **complete FALSE witness**
  `p=2 u=[] v=[a] x=[cycle{!a}]`, technique `acc2+daisystar`; the verifier fails it:
  `VERIFY: fail pattern=11111`. A sub-language witness crossed the acceptance
  decomposition without a valid lift — stage-2's failure mode reproduced on 2 states.
- Incidental: the NOT_LTL diagnosis prose is concatenated twice on the decomposed
  path; the gate-level NOT_LTL carries no technique tag.

## The peel-lift side condition (from discussion; not yet in code)

The daisy lift argument needs the stem letter to be the run's *only* continuation past
`q`: `ℓ⁻¹L = L(dst_k)` only when `ℓ` enables neither a petal nor a sibling stem.
Overlap makes `ℓ⁻¹L` a union, and non-LTL-ness does not survive union — neither the
verdict nor the family lifts. Direction (user): on a NOT_LTL child, **determinize the
exits before lifting** (cheap on a single-state daisy — and the gate reads a
determinized form anyway) and re-check the lift holds; otherwise decline to lift.

## Fix list (priority order)

1. **Self-checking gate**: absorbing `NOT_LTL` only with a witness the gate has itself
   replayed in-process (bounded); otherwise **ABSTAIN** — a non-absorbing decline that
   never builds (the cascade is unsound there) but lets other arms run. Fixes
   `gf_aa_parity`; demotes the acc2 false certificate to at worst a non-absorbing decline.
2. **Widen completion**: all phase pairs × all `v`-orbits (today: first anchor,
   adjacent pair only — `witness.py` `_cycle_state`/`_distinguish`).
3. **ω-power witness shape**: extraction (anchor the orbit inside the lasso cycle),
   `Witness` serialization (extend the `NOT_LTL:` line format), verifier replay.
   Needed for `evenblocks` to be *certified* rather than asserted.
4. **Lift audit**: daisy disjointness side condition (or determinize-then-lift);
   every decomposer that propagates a NOT_LTL witness (acc2/strength/scc) must
   re-validate the lifted family against its own input or drop it to incomplete.
5. **Cheap wins**: technique tag on NOT_LTL results; dedup the doubled diagnosis prose.
6. **Docs**: `tester/algorithm.md` + `nonltl.md` quotient paragraph → cite Thomas
   (counter-free det Muller ⟹ star-free; EL reduces to Muller via inf-sets).

## Census angle (later)

genaut sweep: rows where the gate reads non-aperiodic but no witness (either shape)
completes, cross-checked against any other arm finding a verified-equivalent formula
= more spurious fixtures for free. Ground truth at census sizes is feasible via the
acceptance-enriched syntactic check. Conjecture worth probing: does every spurious
group at minimal size have a same-size aperiodic sibling (the `GF(aa)` pattern)?

## Status (2026-07-01, end of session)

Fixes 1–3 LANDED (docs first, then code — see HISTORY):
- fail-safe gate (certified-or-decline; plus the oracle-could-not-run fence,
  `definable=None`, same never-build behavior, own reason);
- exhaustive linear completion (`witness/linear.py`: all cycles ≥ 2 × all pairs,
  pattern read-back period);
- ω-power shape end-to-end (`witness/{enriched,omega}.py`, `Witness.y`,
  `verifier.verify_omega`): evenblocks certifies at the top gate
  (`p=2 u=[] v=[a] y=[a; !a]`, VERIFY ok `01010`); gf_aa_parity declines after
  exhausting BOTH shapes; technique tag on NOT_LTL landed with fix 1.

**Fix 4 is the open front**, now cleanly isolated by the evenblocks default run:
the acc2 *child* gate certifies a linear family against its own sub-language and
the verdict rides up `credit` unrevalidated — `credit` keeps the FIRST witness
(result.py ~L194), so the top gate's correct ω-power family is shadowed by the
child's stale one, and the doubled diagnosis prose is the same crediting. Also:
for an intersection split (acc2), child-NOT_LTL ⇏ parent-NOT_LTL *in principle* —
the propagation needs replay-against-own-input at the decomposer, per
`witness/algorithm.md` (Lifting). Remaining from fix 5: dedup the diagnosis
accumulation. Validation survey after fixes 2–3: delegated (survey was SUCCESS
83/83 TRUE after fix 1).

## Trust model for the certificate (settled in discussion)

Representation-independent words checked against the *input*; no replay ⇒ zero trust;
replay-ok ⇒ high trust *because* `_cycle_state` computes the exact `p`-cycle on the
discovery form (cycle, not spiral) — the replay only needs to catch transport
corruption (the daisy-`u` bug class, and now the acc2 lift). Optional zero-trust tier
if ever wanted: the checker determinizes the input itself and samples `n` up to its own
stabilization bound (`lag + lcm(ρ, p)`), making the periodicity a theorem with no
producer trust. Lifted witnesses sit one trust notch lower until fix 4 lands.
