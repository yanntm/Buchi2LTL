# The Büchi cascade translator

A leaf of the kr cascade engine: it reads the LTL of an automaton whose acceptance is
a plain Büchi condition (recurrence, Π₂ of the temporal hierarchy) directly off the
Krohn-Rhodes cascade, as a disjunction of "infinitely often in an accepting
configuration".

## Setting

The kr engine translates by decomposing the normalized deterministic automaton D into
a Krohn-Rhodes holonomy cascade and reading LTL off it. A **cascade translator**
labels that cascade:

```
Label             =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
CascadeTranslator =  CascadeHolder → Label
```

`CascadeHolder` wraps the decomposed `Cascade` with this build's caches/counters (see
[`kr/cascade`](../cascade)); the adapter [`kr/aut2cas.py`](../aut2cas.py) lifts a
cascade translator to a `Language → LTLResult` `Translator` by first decomposing the
Language. The contract itself is [`kr/cascade_translator.py`](../cascade_translator.py).

## When it applies

The member is **self-gating** (`is_buchi_cascade`): it declines unless D carries a
plain Büchi condition `Inf(0)`. A run is then accepting iff it visits the accepting
set infinitely often — recurrence.

## The formula

The cascade exposes **configurations** (the reachable states of the holonomy
product). Let `Fin(C)` be the formula true on exactly the words whose run visits
configuration `C` only finitely often (Lemma 7 of the construction; [`kr/fin.py`](../fin.py)).
Then "visit `C` infinitely often" is `¬Fin(C)`, and a Büchi run accepts iff it is
recurrent in *some* accepting configuration:

```
φ  =  ⋁_{C ∈ acceptingConfigs}  ¬Fin(C)
```

`acceptingConfigs` is the cover-aware `buchi_accepting_configs()` reader: the lift
section would under-approximate on a holonomy cover, so the looser cover set is used.
This stays sound because a *transient* (non-recurrent) accepting configuration
contributes only a `¬Fin(C) ≡ false` disjunct, which adds nothing.

## Degenerate case

No accepting configuration ⇒ the empty disjunction ⇒ `φ = false`: a Büchi automaton
with no recurrent accepting configuration accepts the empty language.

## Soundness

Exact on its fragment (Büchi-condition cascades) and declines otherwise — never a
wrong formula. The disjunction is a position-0 language union over configurations,
each `¬Fin(C)` the recurrence reading of one configuration.
