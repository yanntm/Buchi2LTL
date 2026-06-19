# genaut — exhaustive small-TGBA generation experiment

A standalone experiment (NOT wired into the `aut2ltl/` package): exhaustively
enumerate every tiny ω-automaton of a fixed shape, reduce each with Spot, and run
`aut2ltl` over the survivors to measure coverage and surface interesting cases.

The first instance is **2 states / 1 AP / 1 acceptance set** (TGBA). It may later
extend to more states / APs / acceptance sets — but exhaustive enumeration does
not scale far, so this is a one-off census, not a permanent corpus generator.

## The slot model

States `q0`, `q1`; **`q0` is always the initial state**. For every ordered pair
`(src, dst) ∈ {q0,q1}²` and every acceptance value `mark ∈ {unmarked, marked}`
there is one **edge slot**, whose guard is drawn from `{0, a, !a, 1}` with `0`
meaning "edge absent". That is `2·2·2 = 8` slots, each with 4 choices:

    4**8 = 65536 raw automata.

With a single AP this slot set is **fully general**: a marked `a` self-loop plus
an unmarked `!a` self-loop is a genuinely distinct automaton, and `a`-marked +
`!a`-marked = `1`-marked, so parallel edges are covered too. We deliberately do
*not* hand-prune (e.g. dropping a "useless" `q1→q0` edge): full enumeration plus
dedup cannot accidentally miss a language.

## Pipeline

1. **Generate** all 65536 combos (`enumerate.py`), running **one**
   `spot.postprocess(Generic, Small, High)` pass on each. Generic keeps the
   acceptance *family* (no degeneralization / determinization); Small is a
   polynomial structural reducer.
2. **Dedup — two layers, both in-memory and PRE-write (a twin is never built into
   a file).** First *byte-identical*: skip a result whose md5 was already emitted
   (first generator-id wins). Then *AP-canonical*: fold the `a ↔ !a` polarity /
   AP-rename twins via the shared `tests/benchmark/normalize` key
   (`polarity ∘ names`) — only the byte-distinct survivors pay this cost. Folding
   a relabeling is not a different test of `aut2ltl`, just a renamed one; we still
   intentionally do *not* dedup by language or isomorphism beyond relabeling, so
   language-equivalent-but-genuinely-differently-shaped encodings are KEPT (a
   round-trip through `aut2ltl` *should* recover the same formula, but that is the
   thing we want to measure, not assume). The AP-canonical key is reused verbatim
   from the shared tool, so this pre-process carries to any future family regen.
3. **Survey** the survivors through the real front end with the repo's
   `tests/survey.py` (per-case 15s build + 15s verify budgets, spot
   `are_equivalent` oracle):

       python3 tests/survey.py genaut/raw/*.hoa

Each survivor keeps its **generator id** in its filename (`aut_<index>.hoa`), so
the exact raw automaton is reproducible from the index alone (`aut_at(index)`).

## Headline results (2-state / 1-AP / 1-acc census)

- 65536 combos → **1845** byte-distinct → **929** AP-canonical survivors (the
  `a ↔ !a` polarity / AP-rename twins folded pre-write).
- `aut2ltl` answered **922 / 929**: **799 LTL formulas built** + **123 decided
  not-LTL**; **7 build-timeouts**; **0 crashes, 0 declines**.
- Spot verification of the 799: **745 equivalent, 0 NOT-equivalent**, 54 too
  large to flatten/check. **Clean.** Total build 516.5s.

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

## File map

    research_log.md  dated, dense log of observations (idea/validation/results/
                     conclusions) with reproduction pointers.
    enumerate.py     the generator: slot model, build_aut, postprocess + two-layer
                     pre-write dedup (md5, then AP-canonical polarity∘names), and
                     per-index helpers combo_at(i) / aut_at(i, bdict).
                     `python3 genaut/enumerate.py [LIMIT]`  -> genaut/raw/*.hoa
    probe_post.py    diagnostic: rebuild a raw automaton from its generator id and
                     run a spot postprocess type×pref×level matrix on it.
                     `python3 genaut/probe_post.py [INDEX]`   (default 51142)
    probe_true_collapse.py
                     diagnostic: over all 654 universal survivors, does the strong
                     determinizing setting reach the canonical 1-state true? (yes,
                     654/654).  `python3 genaut/probe_true_collapse.py`
    raw/             enumerate.py's scratch output dir (gitignored, regenerable in
                     ~1.7s). The validated, git-tracked snapshot lives in corpus/.
    corpus/          the canonical automata, one subfolder per shape (git-tracked):
                     corpus/2state1ap1acc/ = the 929 AP-canonical survivors. The
                     specimens exist independently of aut2ltl; index naming stable.
    logs/            the committed survey results for the census above:
                     genaut.csv (per-automaton), genaut.summary.txt (the SUCCESS
                     report), genaut.run.log (per-case stderr trace).
