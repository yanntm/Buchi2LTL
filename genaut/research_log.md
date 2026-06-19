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
