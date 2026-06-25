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
3. **Survey** the survivors with the repo harness — genaut's corpus is just
   another reference corpus, run and refreshed exactly like the ones in
   [`../results/README.md`](../results/README.md) (the authoritative workflow:
   rerun into scratch, diff, overwrite only when clean). The corpus folder is
   `corpus/2state1ap1acc/`:

       python3 -m survey --folder genaut/corpus/2state1ap1acc \
           --logs logs/rerun/genaut > logs/rerun/genaut/SUMMARY.txt

   The committed reference run lives in `logs/` (`default.csv` + `SUMMARY.txt`),
   same naming as `results/reference/<corpus>/`.
4. **Analyse** the run into a frontier report (pure CSV post-processing, no tool
   re-run) — text digest to stdout plus a multi-page PDF with log-scale plots:

       python3 genaut/analyze_frontier.py logs/rerun/genaut/survey_*.csv \
           --out logs/frontier.pdf

   The committed `logs/frontier.pdf` is part of the experiment: regenerate it
   whenever the survey is refreshed.

Each survivor keeps its **generator id** in its filename (`aut_<index>.hoa`), so
the exact raw automaton is reproducible from the index alone (`aut_at(index)`).

## Headline results

Browse [`logs/`](logs/) for this census's reference run: the per-automaton CSV,
the SUCCESS summary, and a multi-page PDF analysing the data (regenerate the PDF
with `analyze_frontier.py`).

## File map

    research_log.md  dated, dense log of observations (idea/validation/results/
                     conclusions) with reproduction pointers.
    enumerate.py     the generator: slot model, build_aut, postprocess + two-layer
                     pre-write dedup (md5, then AP-canonical polarity∘names), and
                     per-index helpers combo_at(i) / aut_at(i, bdict).
                     `python3 genaut/enumerate.py [LIMIT]`  -> genaut/raw/*.hoa
    analyze_frontier.py
                     the analysis: one frontier report from a survey CSV (pure CSV,
                     no tool re-run) — ventilation (LTL/not-LTL/ambiguous), idiom
                     collapse, size frontier, routes-to-true, build/verify. Terse
                     digest to stdout + a multi-page PDF with log-scale plots.
                     `python3 genaut/analyze_frontier.py [CSV] [--out PDF] [--top N]`
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
    logs/            the committed reference run for the census above (new-schema,
                     same naming as results/reference/<corpus>/): default.csv
                     (per-automaton survey), SUMMARY.txt (the SUCCESS report),
                     frontier.pdf (analyze_frontier.py's report).
