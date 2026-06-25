# aut2ltl.portfolio.recipes — the recipe catalog & build hub

A **recipe** is a builder `Options -> Translator` registered in the `RECIPES` dict
(`__init__.py`). The registry is the single source of truth: the CLI (`--use <name>`),
the survey and the benchmark all resolve names straight from it. Which recipe ships as
the **default** is the `RECIPES["default"]` alias and nothing else — re-point it to
change the default; that recipe *evolves*, so it is deliberately **not named here**
(read the registry).

Recipes are load-bearing — each one is an algorithm in its own right, sometimes with a
real tradeoff. This page is the **dev hub**: the closed recipes you can `--use`, then
the bricks you build new ones from. For the package wiring see
[`../README.md`](../README.md); the reusable blocks live in [`../builder.py`](../builder.py).

The four layers, lowest first:

```
service primitives   first_success ⊕ · best_of ⊞ · compose ∘ · recurse fix · Memo · the Rewriter kit
       ↑ assemble into
combinator bricks    child -> Translator : peels (daisy…), decomp decorators, roundtrip_best
       ↑ close over a leaf into
closed recipes       Options -> Translator : terminal (one assembly) · advanced (best_of / round trips)
```

A recipe is typically `compose(<decorators>)(<leaf>)` under a final `Simplify(…, "hi")`,
with peels woven into the chain and `core` as the floor.

## Closed recipes — the `--use` vocabulary

Take only `Options`, yield a whole `Translator`. None take a child (they are *closed*).

### Terminal — one linear assembly

| recipe | what it is |
|---|---|
| `best` | `strength ∘ acceptance ∘ daisy` peel over `core` (partscc, else the bls cascade). The historical default. |
| `best_daisy2` | `best` with the length-1 star `daisy2` slipped into the peel (the `daisy/daisy2` pair). |
| `best_inv` | `best_daisy2` with the safety invariant `G(Σ)` factored **once at the top**; the global `Σ` is usually vacuous → benchmark-neutral. |
| `best_inv_loop` | the invariant stripped at **every peel descent** (`daisy_pair_inv`), where the local `Σ` actually fires. |
| `best_inv_all` | invariant woven at **every boundary** (top + pre-`Acc` + per descent). Experimental, A/B for size. |
| `nobls` | the rich decomposition+peel stack floored on `PartScc` **alone — no cascade**; declines where only `bls` could answer. Also the labeler inside `deep_nobls`. |

### Advanced — best_of layering / round trips (compose other recipes)

| recipe | what it is | child arg? |
|---|---|---|
| `cake` | shy `best_of` over `best_daisy2` (the one cascade) + one cheap `PartScc`-only rich variant; displaces the incumbent only on a *significant* size win. | no |
| `cakeds` | `cake` with the `daisy → daisy2 → daisystar` **trio** peel. | no |
| `cakedsdet` | `cakeds` with the deterministic anchored read-off `daisystardet` ahead of the flat `daisystar`. The standard forward **seed**. | no |
| `roundtrip` | `cakedsdet` behind **one** top-level Language round trip. Can regress — superseded by `roundtrip_best`. | no |
| `roundtrip_best` | never-regress round trip `best_of([Memo(C), Roundtrip(Memo(C))])`; the registered form closes `C = cakedsdet`. | **yes** — `roundtrip_best(child)` is exposed |
| `roundtrip_decomp` | split the seed's top-level `∧`, re-present each conjunct, keep the smaller. | no |
| `deep_nobls` | `cakedsdet` seed, then a **deep bottom-up** round trip re-presenting every DAG node via `nobls` (never-regress per node). Collapses the buchi towers; leans on the retranslate budget (`language.translate_tree_limit`). | no |

## Combinator bricks — `child -> Translator`

The higher-order pieces recipes are assembled from. Each takes a child translator and
delegates to it.

### Peels & leaves ([`../builder.py`](../builder.py))

- `core(options)` — `first(partscc, bls)`, the standard floor.
- `bls(options)` — the FoSSaCS Krohn–Rhodes cascade engine alone.
- `daisy(child)` / `daisy_pair` / `daisy_trio` / `daisy_trio_det` (+ `_inv` variants) —
  recursive self-loop / star peels; each labels one center and delegates its exits to
  `child`. `daisystardet` is the deterministic read-off (see
  [`../../daisystardet/algorithm.md`](../../daisystardet/algorithm.md)).

### Decomposition decorators ([`../../decomp`](../../decomp))

`Decorator`s (child → Translator), all *split → label parts → recombine*:

- `StrengthDecompose` (∨ weak/terminal/strong), `SccDecompose` (∨ accepting SCCs),
  `AccDecompose` (∧ acceptance conjuncts, on the deterministic form),
  `Invariant` (factor `G(Σ)` out front; see [`../../decomp/inv/algorithm.md`](../../decomp/inv/algorithm.md)).

### Recipe-level combinator

- `roundtrip_best(child)` — the never-regress round-trip wrapper; the `*_recipe` form
  closes it over `cakedsdet`.

## Service primitives — the algebra

Small, single-concern bricks; the combinators above are pure wiring of these. Soundness
(faithful-or-decline) is closed under every one, so any recipe is sound by construction.

- **`first_success` (⊕)** — *choice*: a flat chain, take the first non-declined result
  ([`../../first_success.py`](../../first_success.py)). ¹
- **`best_of` (⊞)** — *size choice*: run the arms, keep the one a comparator prefers
  (`significantly_smaller`) ([`../../best_of/README.md`](../../best_of/README.md)).
- **`compose` (∘)** — function composition of decorators; unit `identity`
  ([`../../compose.py`](../../compose.py)).
- **`recurse` (fix)** — *self-reference*: `recurse(step) = leaf` with `leaf = step(leaf)`,
  the recursive-descent seam the peels / decomp composites share
  ([`../../recurse`](../../recurse)).
- **`Memo`** — the one sharing-aware brick: a single child run shared across arms
  ([`../../memo`](../../memo)).
- **The Rewriter kit** — `Rewriter = LTLResult -> LTLResult`, re-present an
  already-built formula by going back through its language:
  - `Roundtrip` (one located node), `deep_roundtrip` (whole DAG, bottom-up, one
    memoized pass — [`../../roundtrip_deep/algorithm.md`](../../roundtrip_deep/algorithm.md)),
    `roundtrip_decomp` (a node's operands);
  - `identity` / `relabel(Λ)` / `as_translator(seed, rewriter)` — the floor, a node's
    language round trip, and *seed-then-rewrite* ([`../../ltl_rewriter`](../../ltl_rewriter)).
  - The algorithm for the located-node case is [`../../roundtrip/algorithm.md`](../../roundtrip/algorithm.md).

> ¹ `first_success` currently lives as a bare module rather than a peer package
> (`recurse`/`memo`/`best_of` are packages). TODO: promote it to its own folder.

## Adding a recipe (the whole wiring)

Two lines:

1. **Declare** it as a builder `Options -> Translator` in a new `recipes/<name>.py`
   (compose `builder.py` blocks; reuse an existing recipe as the template).
2. **Name** it: add `"<name>": <name>` to the `RECIPES` dict in `__init__.py`.

The CLI, survey, benchmark and `--use`-sweep scripts all read the registry, so nothing
else needs wiring. When a recipe grows into a complex assembly that deserves a spec of
its own, promote it from a module to a `recipes/<name>/` **package** (an `__init__.py`
exporting the builder + an `algorithm.md`) — the import and the registry entry are
unchanged, so the move is invisible to callers and reversible.
