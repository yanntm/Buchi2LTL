# aut2ltl.portfolio — the combinators that assemble the translators

This package wires the engine (`bls` cascade) and the (de)composition approaches
(`daisy`, `partscc`, `decomp`) into the shipped default translator and the `--use`
technique vocabulary. Every member here is a `Translator` (`Language -> LTLResult`,
see `aut2ltl.contract`) or a builder of one; the engines stay pure and are composed,
not modified. The object graph IS the config graph — one shared `Options` is
threaded through the whole assembly.

The default path is the **`best_daisy2` recipe**:
`Simplify(strength(acceptance(daisy_pair(core))), "hi")` with
`core = first(partscc, bls)` — split the language by strength (∨ of
weak/terminal/strong), then each part by acceptance conjunct (∧, deterministic form),
peel each atom with the **daisy/daisy2 pair** (self-loop daisy, then the length-1
star `daisy2`), and floor on the bls cascade (via `partscc` where a single terminal
SCC labels cleanly). It replaced the legacy `Decompose / SlDriven / Decompose` graph
and the retired `sl` heuristic engine, which `daisy` (self-loop peel) and `partscc`
(terminal-SCC labeling) subsume. `--use best` is the prior daisy-only assembly;
`--use best_inv` adds the global-invariant layer.

## Modules

- **`build.py`** — `build_portfolio` (the single entry: `None` ⇒ the `best_daisy2`
  recipe; a recipe name ⇒ that assembly; a technique list ⇒ the cited ladder) and the
  `TECHNIQUES` vocabulary for `--use`: the five kr leaves
  (`acc / weak / buchi / cobuchi / muller`) and the integrated cascade `bls`
  (the whole engine). Groups the cited kr leaves into ONE cascade-level
  `first_success` (one GAP decomposition).
- **`builder.py`** — the named assemblies (`RECIPES`): `bls` (the cascade engine,
  lifted over the GAP holonomy decomposition), `daisy` (recursive self-loop peel),
  `core` (`first(partscc, bls)`), `daisy_pair` (the daisy/daisy2 peel pair), and the
  recipes `best`, `best_daisy2` (the shipped default), `best_inv`. `--use <name>`
  resolves here.
- **`__init__.py`** — builds the env-seeded default `Options` (from `KR_OPTIONS`) and
  exposes `build_portfolio` / `TECHNIQUES` / `RECIPES` for callers wanting a variant.

## Layering

Above the engine and the (de)composition approaches; imports them (`bls`, `daisy`,
`partscc`, `decomp`) and the `aut2ltl.contract` floor, never the reverse. A caller
builds a variant by rebuilding with `build_portfolio` + a cited technique set, a
recipe name, or a cloned `Options` (the A/B move).
