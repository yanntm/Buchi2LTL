# Witness stage 2 — making every reported non-LTL witness replay-clean

> Untracked working note (like `nonltl.md`): context + plan for stage 2, written so a
> fresh session can pick it up. Not a committed artifact. Stage 1 (cabling) landed
> 2026-06-30 — see `docs/HISTORY.md`. The durable conclusions, once proven, fold into
> `witness/algorithm.md` + the soundness TODO.

## Where we are (stage 1 landed)

The non-LTL witness is now a **first-class, replayed** result:

- the front end prints it machine-readably on stdout: `NOT_LTL: p=… u=… v=… x=…`
  (kind-tagged, ASCII, Spot word syntax); `Witness.serialize()/.parse()` round-trip it;
- `aut2ltl/verifier/` replays a family `(u,v,x,p)` against an automaton by **membership**
  (Spot lasso-intersection, acceptance-agnostic) and reports whether `u·vⁿ·x` toggles
  with period `p`;
- the **survey** runs that verifier on every NOT_LTL row and fills `validation` in the
  LTL vocabulary (TRUE/FAIL/TIMEOUT/ERROR) + a `check_s` time column. An incomplete or
  non-toggling family is **FAIL**, which trips the hard run gate (an uncertified NOT_LTL
  is unsound).

**The stage-2 oracle** is the verifier, run by hand per case:

```
python3 -m aut2ltl <input>                       # prints the NOT_LTL: ... witness line
python3 -m aut2ltl.verifier <input> "<that line>"  # VERIFY: ok|fail|no-witness + pattern
```

**The target set** (kinska scan): **9 NOT_LTL rows FAIL**, all in
`samples/kinska/counting/2ap/` — `counting_buchi_2ap_{05,07,08,09,10,20,21,22,23}.txt`.

## The two failure modes — plan for BOTH

**(1) Incomplete witness (no `x`).** `serialize()` emits `p=… v=[…] incomplete`; replay
→ `VERIFY: no-witness` → FAIL. Cause: `_distinguish` compares only **adjacent** phases
(`witness.py`, the `t[q]` call ~L123), so a count that surfaces only between
*non-adjacent* phases yields no separator; or the group is a genuine determinisation
artefact (spurious — no `x` exists). Sound-but-incomplete, per `nonltl.md` /
`witness/algorithm.md`.

**(2) Complete but non-toggling.** Replay pattern does not toggle with `p`. **CONFIRMED**
on `counting_buchi_2ap_07`:

```
witness: p=2  u=[]  v=[a & !b]  x=[cycle{!a & b}]
u·vⁿ·x  (n=0..2p):  pattern = 1 0 0 0 0   -> VERIFY: fail
```

In `L` only at `n=0`, then constant out. Two readings both produce this, and it is **not
worrying** — the cause is understood:
- a **bad `u`** (wrong prefix): the walk starts from the wrong state, so only the `n=0`
  sample happens to land in `L`;
- a non-closing orbit: phase 2 ≠ phase 0, so `v`'s concrete order on the reached state is
  not `p`.
For `07` the prime suspect is **`u`** — see the confirmed daisy finding below.

## Wiring facts (confirmed by grep this session — report, don't re-derive)

- `extract_witness` is called from **exactly one site**: `gate.py:96` (plus a probe,
  `witness/pin.py`). So the reported witness always comes from the gate, over the
  Language **that gate instance receives**, via `det_generic_minimal()`.
- `definability_gate` is the **outer** decorator (`gate.gated()`: on a non-definable
  language it returns NOT_LTL+witness *without calling `inner`*). It wraps rungs at
  `portfolio/build.py:96,102` and `builder.py:50` (and `bls/__init__.py:45`).
- **Partly answered:** the gate *does* see peeled sub-languages — **daisy** is confirmed
  to reach a NOT_LTL core after consuming a prefix, so its witness is over a sub-automaton
  (see the daisy finding below). `build.py:96` gates `as_translator(chain)` as the
  outermost wrapper, but `chain` peels *inside*, and the gate is the cached choke point hit
  on each (sub)Language. Remaining question: do the *other* decomposers
  (`strength/acceptance/scc`) also route split sub-languages through the gate? **Probe O on
  the non-daisy residue settles it.**

## CONFIRMED: daisy corrupts `u` (the peel mechanism, made concrete)

**`u` is currently wrong on any technique line that contains `daisy`** (user-confirmed).
The daisy self-loop peel reaches the NOT_LTL **core** after consuming a prefix off the
source; the gate then extracts the witness over that *peeled core*, so `u` reaches the
orbit **in the core**, not from the source's initial state — it is missing the
daisy-consumed prefix. Replayed against the **source** automaton (what the survey does),
the walk starts in the wrong place → exactly the `10000` non-toggle on `07`.

This is Hypothesis B (peeling) confirmed and localised: the witness must be **lifted back
across the daisy peel** — prepend the consumed prefix to `u` — i.e. the witness *travels
up the peel*. So `extract_witness` does run on daisy-peeled sub-languages: the peel happens
**inside** a gated path, not only at the top. (Settle the full picture with Probe O, but
daisy is already a known offender — start there.)

Corollary for stage-2 plumbing: the **NOT_LTL path does not yet report its producing
technique** — the `technique` CSV cell is empty on NOT_LTL rows, because the gate builds
`LTLResult.not_definable(...)` with no technique tag. **Add that soon**: it is the cheap
provenance signal that says whether `daisy` (or another peel) was on the path, and it
makes the suspect triage a CSV filter instead of a per-case rerun. (Probe O is the
heavier, language-fingerprint version; technique reporting is the 80% cheap win.)

## Hypotheses for the remaining non-toggling (beyond the daisy `u` lift)

**A — gate-level completion/anchor bug** (for paths *without* daisy, if any remain; `07`'s
witness is over the input's APs `a,b`):
- `u` does not reach a state on a genuine `v`-orbit of length `p` — the
  `_cycle_state` / `_word_to` anchoring mis-maps GAP's *abstract* orbit to the *concrete*
  reached state (the `10000` signature: orbit fails to close);
- `v` lifted in the wrong composition order — GAP acts on the **right** (documented gotcha
  in `witness/algorithm.md`); `v` may need reversing;
- `masks`/`valuations` map `det_generic_minimal` letters to source-replayable letters
  incorrectly.

**B — peeling** (the "travels up the chain" concern): the verdict+witness came from a
**decomposed sub-translator**; `(u,v,x)` describe runs of a *sub*-automaton. Letters can
still be over the input APs yet the orbit/anchor lives in the sub-state-space → wrong walk
on the full input → non-toggle. Only live if Probe O shows a sub-language origin.

## Probes we'd need

Placed under `tests/probes/…`, single-input argv, ≤15 s each, long output → `logs/`
(never `/tmp`). Per CLAUDE.md debug method: ground sub-terms against GT automata from
`D`'s semiautomaton (`tests/bls/trace_fin_semantics.py` pattern), find the first
divergence, fix against the construction reference.

- **Probe T — triage (per case).** Print `witness.complete`, `u/v/x`, the replay pattern
  on the **source** automaton **and** on `det_generic_minimal()` of the input.
  - toggles on `det_generic_minimal` but not source ⇒ representation/letter mismatch;
  - fails on both ⇒ extraction/anchor bug, independent of the source.
  (Extend `tests/probes/bls/definability/witness/replay.py` / the new verifier test.)
- **Probe O — origin/provenance.** Tag which translator + which input Language emitted the
  NOT_LTL result. Cheap precursor (do first): **report the producing technique on the
  NOT_LTL path** (the `technique` cell is empty today) — then `daisy` lines are a CSV
  filter. Heavier version: instrument `gate.gated()` to stamp `id(lang)` / a language
  fingerprint on the `LTLResult` diagnosis; compare to the top input. **Settles the peel
  picture; daisy is already a known offender.**
- **Probe G — GAP lift.** Dump the factorization, the lifted `v`, and `v`'s induced
  transformation on `det_generic_minimal`; assert order `== p` and check the right-action
  composition direction. Reuse `witness.py:_induced_transform` (already imported by
  `witness/pin.py`).
- **Probe C — concrete-orbit grounding.** From the input semiautomaton, walk `u` then
  iterate `v`; assert the visited states are `p` distinct and cycle. Find the first
  divergence between the abstract GAP orbit and the concrete walk — that is the bug.
- **Probe P — all-phase-pairs.** For the *incomplete* cases, try `_distinguish` across
  **all** phase pairs (not just adjacent `t[q]`); does an `x` appear? (Prereq fix below.)

## How we chase the peel

0. **Daisy is already confirmed** to corrupt `u` (above). Start by adding technique
   reporting on the NOT_LTL path, filter the 9 for `daisy`, and fix the daisy `u`-lift —
   that likely clears most of them. Then handle whatever remains.
1. Run **Probe O** on the residue → does any verdict originate **below** the top gate via a
   *different* peel (strength/acceptance/scc), not just daisy?
2. **If yes:** read `portfolio/build.py` + `decomp/{strength,acceptance,scc}` for how a
   split sub-language reaches a gated rung. The witness must be **lifted back through the
   decomposition**: each decomposing translator that *propagates* a NOT_LTL witness (via
   the result algebra `credit`/`fuse`, `aut2ltl/result.py`) must map the sub-witness
   words/orbit to **its own** input alphabet/structure — the witness "travels up the
   chain," inverse to how the decomposition descended. Design: give the NOT_LTL
   propagation a Witness-transform hook per translator, analogous to formula composition.
3. **If no** (all from the top gate): peeling is *not* the cause here — it is purely the
   gate-level anchor/lift bug (Hypothesis A), fixed in `witness.py`.

## How we deal with non-toggling

- **Daisy `u`-lift (start here — confirmed cause):** prepend the daisy-consumed prefix to
  `u` so the family is expressed over the *source*, not the peeled core. Generalise to: any
  peeling translator that propagates a NOT_LTL witness lifts `u` (and, where it relabels,
  `v`/`x`) back across its own peel.
- **Anchor fix:** re-derive `(u,v)` so the *concrete* walk realises the *abstract* orbit;
  verify against the semiautomaton (Probe C) before trusting; fix the GAP composition
  order if reversed.
- **Valuation fix:** ensure `masks`/`valuations` map `det_generic_minimal` letters to
  source-replayable letters.
- **Lift-through-peel:** if Probe O shows sub-language origin, implement the witness lift
  on the propagation path (above).
- **Self-checking gate (the soundness payoff):** the gate emits NOT_LTL **only** with a
  witness it has itself replayed (run the in-process `aut2ltl.verifier`, bounded, before
  committing). A non-replayable / incomplete witness ⇒ **ABSTAIN** — a non-absorbing
  decline that never builds a (possibly wrong) formula and never dominates the portfolio —
  not an absorbing NOT_LTL. This closes the `nonltl.md` / TODO soundness item: the survey
  already enforces "no uncertified NOT_LTL" as FAIL; this makes the tool enforce it too.

## How we deal with incomplete (the other mode)

- **Widen `_distinguish` to all phase pairs** (`witness.py` ~L90/L123) — the documented
  prereq; a count surfacing only between non-adjacent phases is currently missed.
- After widening, still no `x` ⇒ genuine spurious group ⇒ **abstain** (per the
  self-checking gate), not FAIL-forever.

## Definition of done

- All 9 `counting/2ap` → `VERIFY: ok`, or a *principled abstain* where the group is
  genuinely spurious (then the row is no longer a NOT_LTL verdict at all).
- The gate self-checks: NOT_LTL only with a replayed witness; else abstain.
- Re-run kinska + benchmark: **0 NOT_LTL/FAIL**. Then regenerate the reference CSVs
  (NOT_LTL rows now carry `validation` + `check_s`; verify `survey.diff.results` tolerates
  the new column) per `results/README.md`.

## Code map (pointers)

- gate: `aut2ltl/bls/definability/gate.py` (`gated()` ~L87; `extract_witness` L96).
- extract/complete: `aut2ltl/bls/definability/witness/witness.py`
  (`_complete_family`, `_cycle_state`, `_word_to`, `_distinguish` ~L90/L123,
  `_induced_transform`).
- GAP group: `aut2ltl/bls/gap/witness_group.py` (factorization, period).
- value type: `aut2ltl/witness.py` (`serialize`/`parse`/`summary`).
- verifier (oracle): `aut2ltl/verifier/` (`verify`, CLI), `algorithm.md` (suggestive tier).
- survey: `survey/verify.py:verify_witness`; `survey/run.py:_validation`;
  `survey/report.py` (`check_s`).
- portfolio wiring: `portfolio/build.py:96,102`; `builder.py:50`; `bls/__init__.py:45`.
- fixtures: `samples/kinska/counting/2ap/counting_buchi_2ap_{05,07,08,09,10,20,21,22,23}.txt`;
  worked example **07** (p=2, complete, pattern `10000`).
- debug method: `tests/bls/trace_fin_semantics.py` pattern (CLAUDE.md).
- prior context: `nonltl.md` (one-way verdict soundness), `witness/algorithm.md`,
  `tester/algorithm.md`.

## Provenance

Stage 1 cabling landed 2026-06-30 (HISTORY). This note is the stage-2 plan — make every
reported witness *replay-clean* (complete **and** toggling) or have the gate abstain.
Confirmed this session: `07` is complete-but-non-toggling (`10000`); the cause is a wrong
`u` (a bad prefix, not worrying); **`u` is wrong on any `daisy` technique line** — the
daisy peel reaches the NOT_LTL core and the witness `u` lacks the consumed prefix (the
fix: lift `u` back across the peel). `extract_witness` has a single call site (gate) but
the gate is hit on peeled sub-languages. Near-term enabler: report the producing technique
on the NOT_LTL path (empty today). Other peels (strength/acceptance/scc) — Probe O on the
non-daisy residue.
