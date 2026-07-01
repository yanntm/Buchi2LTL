# aut2ltl — Project Status & Orientation

Start here. This is a map for a session, not a technique reference.

## Where things stand

The project **works**: it does what the [root README](README.md) claims — reads an
ω-automaton (or an LTL/PSL formula) and returns an equivalent LTL formula, deciding
and giving a checkable witness when the language is not LTL-definable. Sound on the
correctness gate.

The **NOT_LTL verdict is now fail-safe and certified** (phase 3, 2026-07-01/02): the
definability gate absorbs only on a counting family it has replayed in-process against
its input; anything less (spurious group, unrunnable oracle) is a non-absorbing decline
that fences the cascade and lets other translators answer — a wrong absorbing rejection
is impossible by construction. The witness comes in **two shapes** — linear `u·vⁿ·x`
and ω-power `u·(vⁿ·y)^ω` (required for prefix-independent languages, where every
linear family is provably constant) — completed exhaustively (all orbits × all phase
pairs; enriched-monoid candidates) and serialized/replayed by `aut2ltl/verifier/`,
which the survey runs on every NOT_LTL row. A NOT_LTL crossing a language boundary
(the `decompose` combine, a daisy-family peel) is **revalidated against the host
language** or degraded to a decline. Key fixtures:
`samples/fixtures/hoa/definability/` (`gf_aa_parity` — the spurious-group false
reject, now declined; `evenblocks_nonltl` — ω-power-only counting). Remaining fronts
(seam refinements, parent completion without GAP, cascade self-fence, counter-free
sibling search): `TODO.md` and root `witness3.md`.

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
