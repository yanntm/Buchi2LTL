# aut2ltl.portfolio — the combinators that assemble the translators

This package wires the engine (`bls` cascade) and the (de)composition approaches
(`daisy`, `partscc`, `decomp`) into the shipped default translator and the `--use`
technique vocabulary. Every member here is a `Translator` (`Language -> LTLResult`,
see `aut2ltl.contract`) or a builder of one; the engines stay pure and are composed,
not modified. The object graph IS the config graph — one shared `Options` is
threaded through the whole assembly.

Which recipe ships as the **default** is decided in one place — the
`RECIPES["default"]` pointer in `recipes/__init__.py` — and nowhere else; re-point
it to change the default, and the CLI, survey and benchmark all follow. The recipes
themselves are the `--use <name>` vocabulary, built from a common kit of blocks: a
typical assembly is `Simplify(strength(acceptance(peel(core))), "hi")` with
`core = first(partscc, bls)` — split the language by strength (∨ of
weak/terminal/strong), then each part by acceptance conjunct (∧, deterministic form),
peel each atom (self-loop `daisy`, the length-1 stars `daisy2`/`daisystar`), and
floor on the bls cascade (via `partscc` where a single terminal SCC labels cleanly).
This family replaced the legacy `Decompose / SlDriven / Decompose` graph and the
retired `sl` heuristic engine, which `daisy` (self-loop peel) and `partscc`
(terminal-SCC labeling) subsume. `--use best` is the prior daisy-only assembly;
`--use best_inv` adds the global-invariant layer.

## Modules

- **`build.py`** — `build_portfolio` (the single entry: `None` ⇒ the `best_daisy2`
  recipe; a recipe name ⇒ that assembly; a technique list ⇒ the cited ladder) and the
  `TECHNIQUES` vocabulary for `--use`: the five kr leaves
  (`acc / weak / buchi / cobuchi / muller`) and the integrated cascade `bls`
  (the whole engine). Groups the cited kr leaves into ONE cascade-level
  `first_success` (one GAP decomposition).
- **`builder.py`** — the reusable building **blocks** the recipes assemble: `bls`
  (the cascade engine, lifted over the GAP holonomy decomposition), `core`
  (`first(partscc, bls)`), `daisy` (recursive self-loop peel), `daisy_pair` (the
  daisy/daisy2 peel pair), and `daisy_pair_inv` (the peel with the invariant strip
  woven per descent). The recursive peels are built from the two primitive **bricks**:
  `daisy(child) = recurse(λ leaf: first_success([Daisy(leaf), child]))` — i.e.
  `recurse` (self-reference, `aut2ltl.recurse`) over `first_success` (choice,
  `aut2ltl.first_success`).
- **`recipes/`** — the named assemblies, **one module per recipe** (`best`,
  `best_daisy2` the shipped default, `best_inv`, `best_inv_loop`), each composing the
  `builder.py` blocks into a whole. Its `__init__` aggregates them into the `RECIPES`
  registry that `build_portfolio` resolves for `--use <name>`.
- **`__init__.py`** — builds the env-seeded default `Options` (from `KR_OPTIONS`) and
  exposes `build_portfolio` / `TECHNIQUES` / `RECIPES` for callers wanting a variant.

### Adding a recipe (the whole wiring)

Wiring a new assembly in is **declare it and name it** — nothing else:

1. **Declare** it as a builder `Options -> Translator` in a new `recipes/<name>.py`
   (compose `builder.py` blocks; reuse an existing recipe's module as the template).
2. **Name** it: add `"<name>": <name>` to the `RECIPES` dict in `recipes/__init__.py`.

That is the complete wiring. `build_portfolio` resolves `--use <name>` straight from
`RECIPES`, so the CLI (`python3 -m aut2ltl --use <name>`), the survey, the benchmark,
and the `--use`-sweep scripts all honor the new recipe automatically — they read the
registry, there is no separate list to update. (Cited *techniques* — the producer
leaves `acc / weak / buchi / cobuchi / muller / bls` for the research ladder — are the
`TECHNIQUES` vocabulary in `build.py`; a *recipe* is a whole assembly cited alone.)

## Combinator bricks

Two primitives, both sibling modules of this package, compose the translators:

- **`aut2ltl.first_success`** — *choice*: a flat chain, take the first non-declined.
- **`aut2ltl.recurse`** — *self-reference*: `recurse(step) = leaf` with
  `leaf = step(leaf)`, the recursive-descent shape `daisy` / `daisy_pair` / the
  `decomp` composites share. The single seam where `best_of` (size), memoization,
  or a per-descent layer would later land.

## Layering

Above the engine and the (de)composition approaches; imports them (`bls`, `daisy`,
`partscc`, `decomp`), the combinator bricks (`first_success`, `recurse`) and the
`aut2ltl.contract` floor, never the reverse. A caller
builds a variant by rebuilding with `build_portfolio` + a cited technique set, a
recipe name, or a cloned `Options` (the A/B move).
