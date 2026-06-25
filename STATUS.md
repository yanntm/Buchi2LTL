# aut2ltl — Project Status & Orientation

Start here. This is a map for a session, not a technique reference.

## Where things stand

The project **works**: it does what the [root README](README.md) claims — reads an
ω-automaton (or an LTL/PSL formula) and returns an equivalent LTL formula, deciding
and giving a checkable witness when the language is not LTL-definable. Sound on the
correctness gate.

## How to work in it

- The project is **large**. You will be pointed at the part in play — stay there;
  don't wander the tree.
- There is a substantial **test harness and infrastructure**. You'll meet it only
  when the session needs it.
- **Don't read source files unless asked to.** Reasoning from the prose is cheaper
  and usually enough.
- The **markdown is the map**: the root README and the per-package READMEs /
  `algorithm.md` exist to orient you *without* drowning in technique. Read those
  first; reach for code only when a task requires it.

## The four parts (each has its own README)

1. **`aut2ltl/`** — the source package; the dev-facing README is the source map.
2. **`survey/`** — the test harness and validation/diff tooling (the correctness gate).
3. **`results/`** — the committed benchmark collection and the comparison tools.
4. **`genaut/`** — a standalone subproject with its own exhaustive corpus of samples.

Construction history (the why/when) is in `docs/HISTORY.md` — reference, not session-start.
