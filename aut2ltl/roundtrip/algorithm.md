# The roundtrip algorithm

A decorator translator that **re-presents** a language. It asks a child labeler `Λ`
for a formula, re-describes the input language *by that formula* (a fresh Language
whose only description is the formula), and re-labels `Λ` on it. The leverage is that
`Λ` labels a **presentation**, not an abstract language: two Languages denoting the
same ω-language can be handled very differently. By round-tripping through a formula,
roundtrip hands `Λ` a fresh presentation of the same language — on which it often
produces a far smaller formula (a daisy peel, a clean decomposition, a terminal SCC
where the original presentation gave none). It is a **local, single round trip**: one
seed, one re-description, one relabel. It touches no automaton and knows nothing of
how a Language is built or how `Λ` labels — that is all behind the contract. It owns
no global concern — iterating to a fixpoint, choosing the smaller of two answers, and
bounding the recursion are the assembly's, not its.

## Setting

A translator maps a language to a label; this one is parameterized by the child `Λ`
it both **seeds from** and **relabels with**:

```
Label       =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
```

roundtrip uses exactly one floor operation — the Language's **formula builder**:

```
lang(φ)  =  the Language whose description is the LTL formula φ
```

That is the whole novelty. `lang(φ)` denotes exactly the language of `φ`; nothing of
how the input was presented survives. How that Language later represents itself, and
how `Λ` chooses to label it, are behind their own contracts — no concern of
roundtrip's. roundtrip only swaps one presentation of the language for another.

## The relabel

A run of roundtrip is three moves — **seed**, **re-describe**, **relabel**:

```
roundtrip(Λ)(L) =
    let s = Λ(L)                         -- SEED:        a faithful formula for L  (or ⊥)
    in  if s = ⊥ then ⊥                  --              nothing to re-describe; propagate the decline
        else let L' = lang(s.formula)    -- RE-DESCRIBE: the same language, described by the formula
             in  Λ(L')                   -- RELABEL:     label the fresh presentation; this IS the answer
```

The returned label is `Λ`'s answer on `L'`. It carries its own technique provenance
plus the seed's, under a `roundtrip` stamp — then roundtrip steps aside.

### The three moves

- **Seed** (`Λ(L)`). roundtrip has no formula of its own; its input is an automaton.
  It asks `Λ` for *any* faithful formula — typically the heavy general floor (the
  cascade), whose outputs are large but structurally characteristic. A declined seed
  poisons the round trip (`⊥`): there is nothing to re-describe.
- **Re-describe** (`lang(s.formula)`). The seed formula becomes the *description* of a
  fresh Language denoting the same ω-language (see Soundness). A pure contract-level
  move — no automaton, no translation: roundtrip swaps one presentation of the
  language for another and trusts the Language to be what it says.
- **Relabel** (`Λ(L')`). `Λ` runs again on the fresh presentation. This is where the win
  lands: a presentation `Λ` could not exploit on `L` may now be a daisy, a clean
  strength/acceptance split, or a terminal SCC — labelled in near-closed form. A
  declined relabel is returned as `⊥`: roundtrip offers the *re-derivation*, not the
  seed; the seed answer is the child's to provide, elsewhere.

### Degenerate cases (no special-casing)

- **seed declines**: `⊥` — no formula to re-describe.
- **relabel declines**: `⊥` — the re-description bought nothing; roundtrip offers only the
  re-derivation, so it declines rather than echo the seed.
- **already canonical**: when re-describing `L` yields a presentation `Λ` handles no
  differently, the relabel reproduces the seed — a harmless no-op round trip.
  (Repeated round trips reach this fixpoint fast; iterating up to it is the
  assembly's call.)

## The translator

```
roundtrip(Λ) : Translator
roundtrip(Λ)(L) =
    let s = Λ(L) in
    if s = ⊥ then ⊥                       -- seed declined: nothing to re-describe
    else Λ( lang(s.formula) )             -- re-describe, then relabel (faithful-or-⊥)
```

roundtrip never inspects the seed formula and never touches an automaton — it treats
`lang(·)` and `Λ` as opaque. **Two applications of the SAME child**: one to mint a
formula, one to label its re-description. That single seam — `Λ` on both ends of one
re-description — is the whole construction.

## Soundness

roundtrip is **faithful-or-declines**, by construction, never by post-hoc checking.
The relabel's formula is language-equivalent to `L` along a two-link chain, each
link language-preserving:

1. `Λ` is faithful           ⇒  the seed formula `s ≡ L`.
2. `lang(φ)` denotes `L(φ)`  ⇒  `L' = lang(s) ≡ s`.

Hence `L' ≡ L`, so `Λ`'s faithful label on `L'` is a faithful label for `L`. Declines
propagate through the result monoid (a `⊥` seed or relabel yields `⊥`). roundtrip
adds no soundness obligation of its own: it only ever returns one of `Λ`'s own
faithful-or-declined results.

## Why it fires

The seed is faithful but often *ugly* because the **input presented the language in a
shape `Λ`'s structural translators could not exploit** — e.g. a 1-weak-recognizable
language handed over as a genuine multi-state SCC. Re-describing it as a formula gives
`Λ` a *different presentation of the same language* — frequently one it can peel in
closed form where the original gave nothing.

Worked witness (`aut_33300`, 2 states / 1 AP / Büchi): its initial state has a
non-self incoming edge, so it is no daisy; the cascade floor (`buchi`) returns the
faithful but sprawling

```
a & XFa & G((!a | X(!a | X(!a R Fa))) & (a | X(a R (!a | XFa))))      -- 31 tree nodes
```

Re-described by that formula, the same language is one the daisy peel reads off in
closed form — its formula-built presentation is **1-weak** (a transient start feeding
a single self-loop state) — giving

```
a & GFa                                                               -- 5 tree nodes
```

equivalent, six times smaller.
