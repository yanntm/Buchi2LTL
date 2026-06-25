# spot_isolation — per-call translate time bound, and why the subprocess regresses

Session 2026-06-25. Conclusions of the spotrun investigation. The construction-log
record (why/when) is in `docs/HISTORY.md`; this note is the standalone reasoning.

## The goal

Inside one survey build (~15 s budget), `deep_roundtrip` re-presents every DAG node
bottom-up through `formula.translate()`. One runaway translate eats the whole build
budget and kills an answer that was nearly fully collapsed. We wanted a per-call **wall
time bound** so an overboard single translate degrades *that node* (absorbed by
`best_of([identity, …])`), not the build. A real time bound cannot interrupt a Spot C++
call in-process (GIL), so it needs a child process — `aut2ltl/spotrun/` runs the
translate in a killable child under the budget.

## The problem it created

The bounded-child backend **regresses** kinska: `counting_buchi_1ap_18` goes from DAG
**29 → 225** (sound — `validation == TRUE` either way — but ~8× larger). Reproduce:

```
python3 -m survey --hoa samples/benchmark/inputs/kinska/counting-1ap-counting_buchi_1ap_18.hoa
# default (timeout 3, child path)      -> DAG 225
KR_TRANSLATE_INPROC_TREE_LIMIT=100000 KR_TRANSLATE_INPROC_TEMPORAL_LIMIT=100000  (force in-proc) -> DAG 29
```

## Root cause (confirmed against Spot sources)

`formula.translate()` is **not referentially transparent**. Its result depends on
process-global formula-construction history, through this chain (Spot 2.14.5):

1. Every formula ever built gets a global monotonic id — `fnode::next_id_` is a
   `static size_t`, bumped per construction (`spot/tl/formula.cc:1666-1688`); the id is
   *"the number of formulas constructed so far"* (`formula.hh:794-795`).
2. `formula::operator<` orders formulas **by that id** (`formula.hh:790-808`), and Spot
   deliberately refuses pointer ordering *"because it breaks the determinism of the
   implementation"* — i.e. determinism holds only if the construction sequence is
   reproduced identically.
3. The FM translator's state worklist is an **id-ordered `std::set<formula>`**
   (`spot/twaalgos/ltl2tgba_fm.cc:970, 1912`). States are pulled and merged
   (`symb_merge`, default on) in that order, so id-order drives which states merge → the
   automaton shape.

So `translate` is a function of *(formula structure, global construction history)*. Any
`str(f)` reparse builds fresh fnodes with fresh ids → different worklist order →
different (larger) automaton. A fresh process starts at `next_id_ = 0`, an entirely
different id regime. The subprocess backend must ship the formula as `str(f)` and reparse
it (`spotrun/_child.py`), so it is **doubly perturbed and irreducibly unfaithful**.

## What we ruled out (experiments, each one isolated survey run on counting_18)

| hypothesis | test | result | verdict |
|---|---|---|---|
| process transport / HOA permutation | normalize state indices at the intern key | DAG 225 (byte-identical) | **not it** |
| base-automaton numbering | normalize the base in `_base` | DAG 225 | **not it** |
| `bdd_dict` allocation history | translate against a fresh `bdd_dict` | inert (29 stays 29, 239 stays 239) | **not it** |
| dict-on-Language | (implied by fresh-dict being inert) | — | **would not help** |
| **formula object / `str(f)` reparse** | in-proc `spot.formula(str(f)).translate()` | DAG **239** (blows up in one process, no subprocess) | **this is it** |

The `WARM=f` observation (a throwaway in-parent `f.translate()` on the child path
restores DAG 29) is a *symptom* of the same cause: translating the original hash-consed
`f` lays its subformula ids down in the order the later reconstruction expects.

## Decision (the landing)

- **Keep the default.** `spotrun.translate_timeout = 3` and the in-proc barriers
  (`inproc_tree_limit = 100`, `inproc_temporal_limit = 16`) stay; the bounded-child
  backend stays active. Validation stays SUCCESS; the kinska size bump is the accepted
  cost of the per-call time bound (the **ugly duck**), not a soundness issue.
- **State-index normalization kept** (`aut2ltl/ltl/canon.py`, used by `Language.of` and
  `_base`): defensive, free, makes interning robust to index permutation — but note it
  does **not** address this regression (the cause is upstream, in translate).
- **No faithful subprocess time bound is possible via `str(f)` transport.** The only way
  to get both a hard time bound *and* faithfulness would be a **DAG-transport backend**
  (fork-from-main inheriting the formula by CoW, or a broker reconstructing the DAG
  through Spot's interning factory) — the rejected options in the original design. Revisit
  only if the time bound's safety becomes worth that machinery.

## Bootstrapping more debugging

The session's instruments (env-gated probes `KR_SPOTRUN_CMP/REPARSE/INPROC_RT/WARM/
FRESHDICT` + `_debug_compare`, dumping divergent node pairs to `logs/nodes/`) were
committed once then dropped — recover them from that commit in `git log` for
`aut2ltl/spotrun/__init__.py` if further investigation is needed.
