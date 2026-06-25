# genaut research log

Dense, from-us-to-us. Each entry: idea / validation / results / conclusions
(+optional follow-ups). Pointers given for reproduction, not full method.

---

## 2026-06-19 — Exhaustive 2-state / 1-AP / 1-acc TGBA census

- **idea**: enumerate *every* tiny TGBA of a fixed shape, reduce with spot, run
  aut2ltl over the survivors — measure coverage and surface structure, exhaustively
  rather than by sampling.
- **validation**: full 8-slot model (every `(src,dst,mark)` slot a guard from
  `{0,a,!a,1}`, q0 initial) = `4**8` combos; one `spot.postprocess(generic,high,
  small)` pass each; byte-identical dedup (md5, first id wins). Then
  `tests/survey.py genaut/raw/*.hoa` (per-case 15s build + 15s verify,
  `are_equivalent` oracle). Repro: `enumerate.py`, `logs/genaut.csv`.
- **results**: 65536 combos → **1845** byte-distinct automata. aut2ltl answered
  **1831/1845**: 1586 LTL built + 245 not-LTL; 14 build-timeouts; 0 crashes/declines.
  Verify: **1480 equivalent, 0 NON-equivalent**, 106 too large to check. The 1586
  collapse (truncated-string `uniq`) to ~221 distinct formulas.
- **conclusions**: the construction is sound and broadly complete on this space
  (zero wrong answers across the whole exhaustive set). The distinct-form count
  (1845) vastly over-counts distinct languages: the produced-formula side is far
  more concentrated (~221), i.e. structure ≫ semantics in this corpus.

Result analysis. The truncated-string histogram is dominated by a tiny vocabulary
of idioms, in near-perfect `a↔!a` polarity pairs: `1` (×654), `GFa`/`GF!a` (×104
ea), `Fa`/`F!a` (×44), `a`/`!a` (×35), `G(a|Xa)`/`G(!a|X!a)` (×15), then a long
count-1 tail of compound combinations. Read as a census of the Manna–Pnueli atoms
realizable at 2 states / 1 AP / 1 acc set: a handful of keyed languages carry
almost all mass; the 245 not-LTL are the keyless residue (non-aperiodic) the tool
correctly declines.

---

## 2026-06-19 — spot `Small` does not decide universality

- **idea**: 654 survivors reconstruct to `1` (true). If they are universal, why did
  the `Small` pass leave them non-trivial?
- **validation**: tally state counts + det of the 654 (`logs/genaut.csv` rows with
  reconstructed `1`); confirm universality via `complement(a).is_empty()`, NOT
  `spot.is_universal` (that is the structural HOA branching property, not "accepts
  every word"). Repro: `probe_post.py <index>`.
- **results**: all **654 verified `True`** (equiv to true). Only **3** reached the
  1-state canonical under `Small`; **651 stayed 2-state nondeterministic `Inf(0)`**.
  Example `aut_51142`: complement empty (universal) yet `Small` keeps 2 states at
  every level (low/med/high identical).
- **conclusions**: `Small` is a polynomial *structural* reducer (simulations, SCC,
  acceptance cleanup, WDBA-min for *deterministic-weak* only). NBA universality is
  PSPACE; simulation is a sufficient-not-necessary *pairwise* relation and cannot
  see a global "every word has an accepting run". So `Small` provably won't collapse
  these — by design, not bug.

---

## 2026-06-19 — the lever is determinization, and it is complete

- **idea**: what spot setting *does* collapse a universal 2-state blob to canonical
  `true`, and does it work for all 654?
- **validation**: `type × pref × level` matrix on a witness (`probe_post.py`); then
  the strongest cell over all 654 (`probe_true_collapse.py`).
- **results**: only **`generic` + `deterministic` at medium/high** reaches 1-state
  `t`. `small` never does (level irrelevant). `ba`/`tgba` output types stay 2-state
  even with `deterministic` (forced Büchi keeps a set). Over all 654: **654/654**
  collapse, histogram `{1: 654}`.
- **conclusions**: two independent gates — `deterministic` (determinize → see
  universality) AND `generic` (let the now-redundant `Inf(0)` drop to `t`, the
  "merge redundant acc (Medium+)" behavior). With both, the universal barrier is
  *exactly* determinization and nothing else: no residue of genuinely-stubborn
  universal automata in this space. The 651 were one determinization step from
  trivial.

Cross-ref: aut2ltl's own input cleanup (`aut2ltl/language.py::_clean`) is
`postprocess(generic, <level>, **any**)` — pref `any`, never `deterministic` — so
the tool sees the same non-canonical form and *still* produces `1`. The collapse is
the construction's semantic work, not a spot canonicalization we rode on.

---

## 2026-06-19 — which methods key the `true` cases (portfolio routes)

- **idea**: which portfolio members produce `true`, and at what cost?
- **validation**: technique (col4) + build_s (col9) over the 654 reconstructed-`1`
  rows of `logs/genaut.csv`.
- **results**: `acc` 326, `daisy2` 242, `daisy` 84, `daisy+strength2` 2. Total build
  **382.4s** (mean 0.585s, max 1.144s). None used `bls`.
- **conclusions**: ~50/50 split between two *independent* routes to `true` — `acc`
  (the first member to ask for a deterministic view; tries hard to shrink before
  cascade → the determinizing route) and the `daisy*` self-loop peel (a structural,
  non-determinizing route recognizing "all accepting self-loops"). Earlier claim
  "determinization is the only lever" holds at the *spot-postprocess* level; at the
  *portfolio* level there are two paths, only one determinizing. Argues for keeping
  the cheaper non-determinizing peel ahead in priority.

---

## 2026-06-19 — thesis: the formula domain is the leverage; aut2ltl is the key

- **idea**: the automaton hides the language's essence; recovering the LTL idiom is
  where the simplicity lives.
- **validation**: the whole census is the experiment — automaton-level `Small`
  cannot open 651 universal blobs; aut2ltl returns `1` for them, soundly.
- **results**: 1586 opaque acceptance structures → a small readable idiom
  vocabulary, 0 wrong; 245 keyless languages correctly declined.
- **conclusions** (tentative, thesis-level): validity/idiom is syntactically cheap
  in the formula domain but PSPACE-and-structurally-invisible in the automaton
  domain; the construction's value *is* bridging into the formula domain (the hard,
  rare direction: automaton→LTL sound+complete). Caveats we observed, not inferred:
  the bridge itself is the expensive part and does not exist for non-LTL languages;
  and formula leverage ≠ canonicity (LTL has no normal form — we saw
  `G(Fa&F!a)` vs `G(F!a&Fa)` as distinct strings).
- **follow-ups (optional)**: (1) `ltlfilt --equiv`/`-r` over the 221 produced
  strings to fold polarity/operand-order twins → true distinct-language count.
  (2) `spot.mp_class` on each *produced* formula (CSV `mp` is `?` for HOA inputs) →
  histogram of which hierarchy keys dominate. (3) does the `acc` vs `daisy*`
  partition of the 654 fall out along a structural feature (e.g. presence of a
  non-self-loop edge)?

---

## 2026-06-19 — AP-canonical dedup wired pre-write; survey rerun on 929

- **idea**: the byte-identical md5 dedup leaves the `a <-> !a` polarity / AP-rename
  twins (byte-distinct, same language up to relabeling) in the corpus — half the
  files were folding to the same formula a posteriori. Fold them *before* writing,
  reusing the shared normaliser instead of a bespoke key.
- **validation**: add `dedup.default_key` (`polarity o names`, from
  `tests/benchmark/normalize`) as a second in-memory `seen` set in
  `enumerate.py::main`, after the cheap md5 pre-filter (so only the ~1845
  byte-distinct survivors pay the normalise cost). No file is ever written for a
  twin. Confirmed against the standalone `dedup.py --prune` (same 916 dropped).
  Repro: `python3 genaut/enumerate.py` (full regen ~1.7s).
- **results**: 65536 -> **1845** byte-distinct -> **929** AP-canonical survivors
  (916 twins folded pre-write). Survey over the 929
  (`KR_SURVEY_CSV=genaut/logs/genaut.csv python3 tests/survey.py genaut/raw/*.hoa`):
  **922/929** answered (**799** LTL built + **123** not-LTL), **7** build-timeouts,
  **0** crashes/declines; Spot **745 equivalent, 0 NON-equivalent**, 54 unchecked
  (too large). **SUCCESS, clean.** Totals: DAG=211884, temporals=37488,
  build=516.5s — roughly half the 1845 run, as expected from removing the twins.
- **conclusions**: the polarity symmetry that dominated the produced-formula
  histogram is now removed at the source, so the committed census (`logs/genaut.*`)
  is the AP-canonical one. Still zero wrong answers on the deduped space —
  soundness is not an artifact of the redundant twins. The dedup is generic over
  the produced TGBA set (not census-specific), so it carries to any future
  family/shape regen.
- **caveat**: the earlier "true finding" / determinization entries above were
  computed on the pre-dedup 1845 corpus and their absolute counts (e.g. `1` ×654)
  no longer match `raw/`; the probe scripts still reference the original
  generator-ids. The structure stands; re-run the probes over 929 to refresh the
  numbers if needed.

---

## 2026-06-19 — the polarity-class partition of the dedup

- **idea**: reason out exactly what the AP-canonical dedup removed, purely from
  the before/after counts — no file inspection.
- **validation**: polarity normalisation is an involution, so it partitions the
  1845 byte-distinct automata into classes of size <= 2. Arithmetic only
  (removed = 1845 - 929; singletons = 929 - removed).
- **results**: **916 pairs** (size-2 classes: one kept, one removed — the 916 we
  dropped each have their twin still in the corpus) + **13 singletons** (size-1:
  self-image under polarity norm, no distinct twin, so never removed). Check:
  2*916 + 13 = 1845; 916 + 13 = 929. So exactly **13** corpus automata are
  polarity fixed points (use no literal guard, or are a<->!a symmetric); the other
  916 survivors are each the kept half of a folded pair.
- **conclusions**: the dedup is overwhelmingly pair-folding (916 pairs vs 13 fixed
  points) — the 2-state/1-AP space is almost entirely polarity-symmetric, which is
  why the pre-dedup histogram looked like a mirror. Only 13 of 1845 sit on the
  symmetry axis.

---

## 2026-06-19 — refreshed entry 1/2/4 measurements over the 929 corpus

- **idea**: re-run the earlier census measurements on the AP-canonical corpus
  (the thought above explains why the absolute counts should ~halve).
- **validation**: re-aggregate the committed CSV (`genaut/analyze_census.py`,
  pure CSV — the `reconstructed` column is the truncated formula) and re-tally the
  stored true automata (`genaut/probe_true_states.py`, spot over
  `corpus/2state1ap1acc/`, universality via `complement(a).is_empty()`). Entry 3
  deliberately NOT re-run (the determinization diagnosis stands; the lever makes
  sense — left alone).
- **results (entry 1 — census/idioms)**: 799 LTL built; distinct truncated
  formulas **121** (was ~221). Top idioms: `1` x331, `GFa` x65 / `GF!a` x39,
  `Fa` x38 / `F!a` x6, `a` x35, `G(a | Xa)` x15. The histogram is **no longer
  polarity-symmetric**: dedup keeps one automaton per a<->!a pair, so each idiom
  roughly halves but UNEVENLY (normalising the automaton's first literal to
  positive does not fix the produced formula's polarity).
- **results (entry 2 — Small & universality)**: **331** reconstruct to `1`; as
  stored under one Small pass, state histogram `{1: 3, 2: 328}`, determinism
  `{det: 17, nondet: 314}`; all **331** universal (complement empty). Still
  **exactly 3** reach 1-state canonical (those 3 survived dedup intact); the rest
  stay 2-state — finding unchanged from the 1845 run.
- **results (entry 4 — routes to true)**: `acc` 163, `daisy2` 122, `daisy` 45,
  `daisy+strength2` 1; build total 191.3s (mean 0.578s, max 1.146s). The ~50/50
  two-route split holds: `acc` 163 vs `daisy*` 168.
- **conclusions**: every measured structure (idiom concentration, the 3 canonical
  trues, the two-route split, zero wrong answers) survives the dedup; only the
  absolute counts halve — exactly as the polarity-class partition predicts.

---

## 2026-06-25 — moved verbatim from genaut/README.md (former §Headline results + §The "true" finding)

The README no longer carries headline numbers — we do not want to maintain them
there; it now points at the logs/ folder instead. The text below is that former
README section, moved here without curation.

## Headline results (2-state / 1-AP / 1-acc census)

- 65536 combos → **1845** byte-distinct → **929** AP-canonical survivors (the
  `a ↔ !a` polarity / AP-rename twins folded pre-write).
- The corpus **ventilates** into **799 LTL-definable** (a formula was built) +
  **123 decided not-LTL** + **7 ambiguous** (build-timeouts — the only inputs
  whose LTL-ness is undecided); **0 crashes, 0 declines**.
- Spot verification of the 799: **745 equivalent, 0 NOT-equivalent**, 54 too
  large to flatten/check. **Clean.**
- The 799 answers **collapse onto a tiny idiom vocabulary**: **87 distinct
  formulas**, with `1` (true) alone covering **331 (41%)** and the **top-5 idioms
  ~64%**; the flattened size is **median 2 nodes, 80% under 20** — a thin
  exponential tail. See `logs/frontier.pdf` (regenerate with `analyze_frontier.py`).

> **Note — the analysis below predates AP-canonical dedup.** The "true finding"
> and determinization sections were computed on the *pre-dedup 1845* corpus via
> the probe scripts (`probe_post.py`, `probe_true_collapse.py`), which still
> reference the original generator-ids. AP-canonical dedup folds away exactly the
> polarity twins they count (e.g. the `1` ×654 universal class roughly halves),
> so those absolute counts no longer match the 929-file `raw/`. The *structure*
> they describe is unchanged; the numbers are anchored to 1845 until the probes
> are re-run over the pruned corpus.

### The "true" finding

**654** automata have language `true` (all verified). Of these, only **3** were
reduced to the 1-state canonical form by Spot; **651 survived as 2-state
nondeterministic `Inf(0)` automata** that accept every word but were left at full
size. This is *not* a Spot bug: `postprocess(Small)` is a structural reducer, and
recognizing that a *nondeterministic* Büchi automaton is universal is the
PSPACE-complete universality problem — Small deliberately won't pay for it.

`probe_post.py` pins down the lever: across a `type × pref × level` matrix on such
an automaton, only **`generic` + `deterministic` at Medium/High** reaches the
canonical 1-state `t`:

- `deterministic` pref is required — it *determinizes*, so universality becomes
  visible. `small` never does it, at any level (the level is irrelevant here).
- the `generic` type is also required — once determinized, the `Inf(0)` set is
  always satisfied and `generic` lets it be **dropped to `t`** (this is the
  "merges redundant acceptance sets (Medium+)" behavior documented on
  `aut2ltl/language.py::_clean`). Forcing `ba`/`tgba` output keeps a Büchi set, so
  those stay at 2 states `Inf(0)` even with `deterministic`.

And it is a *complete* remedy: `probe_true_collapse.py` runs that strong setting
over all **654** universal survivors and **every one** collapses to the canonical
1-state `t` (state-count histogram `{1: 654}`). So the 651 that `Small` left at 2
states were never "hard" — they were one determinization step from canonical; the
cheap path simply refuses that step.

That redundant-acc drop is exactly why the three 1-state `true` survivors differ:
`aut_00257` had its `Inf(0)` dropped (`Acceptance: 0 t`), while `aut_00265`
reached the same 1-state shape on a path that kept `Inf(0)` (state colored) — the
acc-merge is path-dependent, matching the original "sometimes forgot to drop
redundant acc" hunch.

Why this validates `aut2ltl`: its own input cleanup (`_clean`) is
`postprocess(generic, <level>, **any**)` — pref `any`, never `deterministic`. So
the tool sees the same non-canonical 2-state `Inf(0)` form and *still* produces
`1` — the construction is doing real semantic work, not riding on a Spot
canonicalization we never asked for.

(Aside: `spot.is_universal` is the *structural* HOA property about branching, not
"accepts every word"; test language-universality with `complement(a).is_empty()`.)
