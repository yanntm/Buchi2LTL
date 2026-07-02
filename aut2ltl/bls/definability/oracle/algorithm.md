# Deciding LTL-definability — the syntactic ω-semigroup oracle

The oracle decides, for the ω-regular language `L` of a `Language`, whether an
LTL formula defining `L` exists. It emits no formula; it answers the decision
problem exactly, and on the negative side it hands out a finite,
representation-independent certificate that any third party can check by
membership queries alone.

This document is standalone and deliberately slow: the decision is assembled
in numbered layers, each introducing one object and proving what it carries,
so that every claim can be audited at the layer that makes it. Layers 1–2
state the problem and the certificate; layers 3–5 build the algebra down to
two independently checkable conditions; layers 6–8 compute; layers 9–11 walk
the edge cases, three worked examples, and the exactness argument. The reader
in a hurry can read layers 5, 7 and the examples — but the hurry will cost
more than the layers do.

## 1 — Setting

The contract has three outcomes:

| answer | grounds |
|---|---|
| **LTL** | the syntactic ω-semigroup of `L` is aperiodic — a theorem |
| **NOT_LTL** | a **counting family** was extracted and replayed against the input — the checkable certificate of layer 2 |
| **INCONCLUSIVE** | a resource cap was hit (determinization, monoid size, time) — never an algorithmic blind spot |

Both decided answers are theorems; abstention is only ever exhaustion.

The input is one deterministic form of the language: `det_generic_minimal()` —
determinized to deterministic generic-acceptance (Emerson–Lei), completed.
Write `D` for this automaton, `Q` its states, `C` its acceptance marks
(carried on transitions), `Σ = 2^AP` its alphabet. Completion adds at most a
sink — an idempotent, invisible to every algebraic reading below. **No
minimality is assumed anywhere**: the whole construction is
representation-independent by the time it answers, which is the point.

The decision rests on the classical characterization (Thomas 1979; Perrin
1984; Perrin–Pin, *Infinite Words*; Diekert–Gastin 2008):

```
LTL-definable  =  FO[<]-definable  =  star-free  =  syntactic ω-semigroup aperiodic
```

**Aperiodic = group-free**: no element `s` has a non-trivial cyclic orbit
`s, s², …, s^{a+p} = s^a` with period `p > 1`. A non-trivial group is exactly
the ability to count modulo `p`, which counter-free LTL cannot express. The
syntactic ω-semigroup `S(L)` (Arnold 1985) is the canonical invariant of the
language — independent of any automaton chosen to present it — so aperiodicity
read off `S(L)` is exact in *both* directions. The plan is therefore blunt:
compute the semigroup part `S(L)₊` as a quotient of a finite monoid read off
`D`, power-iterate its classes, and unroll a certificate from any group found.

## 2 — The certificate: counting families

A negative answer must be handed out as an object checkable without trusting
this module. Two shapes:

```
linear    F₁(u, v, x, p) :  n ↦ [ u·vⁿ·x ∈ L ]         toggles with n mod p
ω-power   F₂(u, v, y, p) :  n ↦ [ u·(vⁿ·y)^ω ∈ L ]     toggles with n mod p
```

with `p > 1`; `u`, `v`, `y` finite words; `x` an ultimately-periodic ω-word (a
lasso). "Toggles with `n mod p`" means the membership function is determined
by `n mod p` for **all** `n ≥ 0` and is not constant. Every sample of either
shape is an ultimately-periodic word, so both shapes are checkable by
membership queries alone.

- **Soundness (either shape ⟹ `L` is not LTL).** If `L` were star-free,
  `S(L)` would be aperiodic, so `[vⁿ]` would be eventually constant in `n`,
  making both membership functions eventually constant — contradicting a
  genuine period `p > 1` holding for all `n`. The argument is independent of
  any automaton and of the machinery that produced the family.
- **Completeness of the pair (two shapes, and no third).** The syntactic
  congruence of an ω-regular language separates two finite words by exactly
  two context shapes — linear `x·_·y·t^ω` and ω-power `x·(_·y)^ω` (Arnold
  1985). If `L` is not star-free, some `[v]` has a cycle of period `p > 1` in
  `S(L)`; two of its powers are separated by a context of one of the two
  shapes, and unrolling that separation along the cycle yields a toggling
  family of the corresponding shape. Hence `L` is not LTL **iff** a family of
  shape F₁ or F₂ exists; no further shape is ever required.
- **Both shapes are load-bearing.** If `L` is prefix-independent (`σw ∈ L ⟺
  w ∈ L` for every finite `σ`) then `u·vⁿ·x ∈ L ⟺ x ∈ L`: every linear family
  is constant, on every choice of `(u, v, x)`. Prefix-independent non-LTL
  languages exist — the evenblocks example of layer 10 is one — so F₂ is a
  requirement, not an optimization. Layer 5 will make this blindness *visible
  in the computation*: prefix-independence is exactly "one residual class",
  and the linear half of the congruence then separates nothing.

## 3 — The recognizer: the acceptance-enriched monoid

The algebraic handle on `D` must remember what acceptance reads: the marks
visited *along* a run, not only its endpoints. The **acceptance-enriched
monoid** `EM(D)` does exactly that. The element of a finite word `w` is the
map

```
q  ↦  ( δ(q, w),  marks collected from q along w )
```

with composition `(f, M)·(g, N) : q ↦ (g(f(q)), M(q) ∪ N(f(q)))` — a
transformation monoid on the finite set `Q × 2^C`, generated by the letters.
Write `st_e(q)` and `mk_e(q)` for the two components of an element `e` at
state `q`, and `EM¹` for the monoid with the identity adjoined (the element of
the empty word: `q ↦ (q, ∅)`).

- **The skeleton lemma.** Two finite words with the same enriched element are
  interchangeable in every ω-context: any run through either lands in the
  same states *and* collects the same marks per start state, so — `D` being
  deterministic — the run skeleton of every surrounding ω-word is identical,
  and so is its acceptance. Consequently the syntactic morphism `Σ⁺ → S(L)₊`
  factors through `Σ⁺ → EM(D)`, and the induced map

  ```
  EM(D)  ─►  S(L)₊
  ```

  is a surjective morphism: `EM(D)` recognizes `L`, and `S(L)₊` is a
  computable quotient of it.
- **The enrichment is not optional.** The transition monoid — the same object
  with the marks forgotten — does *not* recognize `L` in this sense: two words
  with equal state maps but different intermediate marks can be separated by
  an ω-power context. This is why a group in the transition monoid proves
  nothing (it can be an artefact of the encoding, resolved in layer 10's
  second example) while a group in the quotient of `EM(D)` will prove
  everything.

## 4 — The congruence

By the skeleton lemma, Arnold's two context shapes act on words only through
their enriched elements, so the syntactic congruence reduces to a relation on
the finite monoid — for `e, f ∈ EM(D)`:

```
e ~ f   iff   ∀ a, b ∈ EM¹, t ∈ EM :   Acc(a·e·b, t) = Acc(a·f·b, t)      (linear contexts)
        and   ∀ a, b ∈ EM¹         :   Acc(a, e·b)  = Acc(a, f·b)         (ω-power contexts)
```

where `Acc(x, c)` is the acceptance of any ω-word `w·z^ω` with `[w] = x`,
`[z] = c`, from the initial state — well defined by the lemma. `EM¹` supplies
the empty context; `t` ranges over non-identity elements (an ω-word needs a
non-empty cycle). Quantifying over elements *is* quantifying over all words,
because words act only through their elements.

**Theorem.** `EM(D)/~  =  S(L)₊`. Hence, by layer 1's characterization, `L`
is LTL-definable iff `EM(D)/~` is aperiodic — and a group in the quotient is
never an artefact of the presentation, because the quotient is the
presentation-independent invariant itself.

As stated, `~` quantifies over triples of monoid elements — computable but
crude. The next layer collapses it.

## 5 — The collapse: two independently checkable halves

**The collapse lemma.** `Acc(x, c)` depends on the prefix `x` only through
the single state `st_x(init)`: the marks a prefix visits are visited finitely
often and never touch the inf-set. Write `A(q, c)` for the acceptance of
iterating `c` from `q` — walk `st_c` from `q` until the orbit closes, union
`mk_c` around the closed cycle, evaluate the Emerson–Lei condition — and
`Aprof(c) = (q ↦ A(q, c))`, a `|Q|`-bit profile. Chasing the collapse through
both quantifications factors the congruence:

```
e ~ f     ⟺    e ~lin f   ∧   e ~ω f

e ~lin f  ⟺    ∀ q ∈ Q  :   L(st_e(q)) = L(st_f(q))        (pointwise residual equality)
e ~ω f    ⟺    ∀ b ∈ EM¹:   Aprof(e·b) = Aprof(f·b)        (right-invariant profile equality)
```

- **The linear half.** `st_{a·e·b}(init) = st_b(st_e(st_a(init)))`, and
  `st_a(init)` ranges over exactly the reachable states as `a` ranges over
  `EM¹`. Fix `q`, and write `s = st_e(q)`, `s′ = st_f(q)`. The remaining
  condition `∀ b, t : A(st_b(s), t) = A(st_b(s′), t)` says `s` and `s′`
  accept the same ultimately-periodic words — and two ω-regular languages are
  equal iff they agree on ultimately-periodic words, so it says exactly
  `L(s) = L(s′)`. Three consequences fall out: the mark parts of `e` are
  entirely irrelevant to `~lin`; the whole `∀ b, t` quantification became a
  `Q × Q` relation computed **once on `D`, with no monoid involved**; and on
  a prefix-independent language every residual is `L` itself, so `~lin` is
  trivially total — layer 2's blindness lemma, now a computation fact.
- **The ω half.** `Acc(a, e·b) = A(st_a(init), e·b)`, and the `∀a` collapses
  to `∀q` the same way — leaving a **right**-congruence condition seeded by
  the profile. No left translation occurs anywhere in what follows; this
  matters, because right-multiplication by a letter is the one operation the
  monoid's BFS table gives for free.
- **One pass suffices.** `~lin` is itself right-invariant (derivatives of
  equal languages are equal: `L(s) = L(s′) ⟹ L(δ_a(s)) = L(δ_a(s′))`), so
  `~` is the coarsest right-invariant equivalence refining a *single* seed —
  computed by one refinement to fixpoint in layer 6, not two.
- **The factoring mirrors the certificate.** `~lin` is exactly what a linear
  family can observe (a tail after the powers), `~ω` exactly what an ω-power
  family can (acceptance around a loop through the powers). The difference
  that produces a verdict already names the shape of its witness — layer 7
  cashes this in.

## 6 — Computing the quotient

Four objects, in dependency order; every translation used is a
right-multiplication.

1. **Closure.** Materialize `EM¹(D)` by BFS from the letter elements under a
   size cap: one shortest representative word per element (elements are met
   shortest-first), and the right-multiplication table
   `element × letter → element` as a by-product. Blowing the cap is
   **INCONCLUSIVE**.
2. **Residual classes.** Compute `≃` on `Q` — `q ≃ q′` iff `L(q) = L(q′)` —
   one language-equivalence check per state × existing class (products on the
   small deterministic form), once, before any monoid-sized work. The `~lin`
   class of an element is then read directly off its vector — the tuple
   `(q ↦ [st_e(q)]_≃)` — with no refinement on this side. The *separator*
   between two inequivalent states (an ultimately-periodic word accepted from
   exactly one) is **not** precomputed: extraction will touch exactly one
   pair, and only that pair pays for a product.
3. **Profiles.** `Aprof(e)` for every element: one `O(|Q|)` pass over the
   functional graph of `st_e` — find each closed cycle, union `mk_e` around
   it, evaluate the condition, propagate to the transients (their marks are
   visited finitely often).
4. **Refinement.** Seed the partition by the pair (`~lin` class, `Aprof`);
   split a class whenever right-multiplication by a letter maps two of its
   members into different classes; iterate to fixpoint (Moore refinement, at
   most `|EM|` splits). By the right-invariance of both seed components this
   single pass computes `~ = ~lin ∩ ~ω` exactly. **No split bookkeeping is
   kept** — the constructive counterpart is the *chase* of layer 7, run on
   demand.

Aperiodicity is then read by power-iterating each class: the class of
`v^{k+1}` is determined by the classes of `v^k` and `v` (the relation is a
congruence), so the class power sequence is detected by its **first repeated
class id** — which also makes the index minimal and the classes around the
cycle pairwise distinct, two facts layer 7 leans on. The identity is
idempotent and skipped; classes already seen are skipped (their sequence is
determined); elements are scanned in BFS order, so the first group found has
a shortest representative word. Every period 1 ⟹ the quotient is aperiodic ⟹
answer **LTL**.

## 7 — Extracting the certificate

A group class `[v]` with period `c > 1` yields a family that **cannot fail to
assemble**. The pieces, in the order they are produced:

- **The pair.** The classes around `[v]`'s power cycle are pairwise distinct
  (layer 6), hence pairwise non-congruent, hence *separated*: two consecutive
  powers `v^a, v^{a+1}` (`a` the index) already suffice.
- **The chase.** Because the refinement reached a fixpoint from the seed,
  two non-congruent elements admit a word `b` with
  `seed(e·b) ≠ seed(f·b)` — a shortest one is found by BFS over the pair
  graph of the right-translation table (the distinguishing-word construction
  of DFA minimization, run forward). Pairs that collapse to equal elements
  are pruned (equal elements never separate); the BFS terminates because the
  pair space is finite and a separating word exists.
- **The base difference names the shape.** At the chase's end the seeds
  differ at some slot `q` — in the `~lin` component or in the profile:
  - a **residual difference**: the states `s = st_{vᵃ·b}(q)` and
    `s′ = st_{vᵃ⁺¹·b}(q)` have `L(s) ≠ L(s′)`. Now, and only now, one
    separator product runs: an ultimately-periodic `w` accepted from exactly
    one of them. The family is **F₁** with `x = b·w`.
  - a **profile difference**: `A(q, vᵃ·b) ≠ A(q, vᵃ⁺¹·b)`. The family is
    **F₂** with `y = b` — and its membership pattern is a pure lookup in the
    profile table already computed; F₂ never touches the automaton again.
- **The anchor.** In both shapes `u` is a shortest word from the initial
  state to `q` — BFS on `D`, not on the monoid; `q` is reachable because
  every state of the trimmed form is.
- **Exact periodicity, from `n = 0`.** Membership of the `n`-th sample
  depends only on the class of `vⁿ`, which is exactly periodic from the index
  `a` on. Absorbing the index — into the anchor (`u ← u·vᵃ`) for F₁, into
  the return word (`y ← vᵃ·y`) for F₂ — shifts the family so the pattern is
  `c`-periodic from `n = 0`. The **declared period** `p` is the minimal
  cyclic period of the membership pattern read around one class cycle (`c`
  cheap evaluations); it is non-constant because the chased pair differs, so
  `p > 1` always.
- **Replay.** The family is material, not yet a verdict: it is replayed by
  membership against the *input* automaton (the engine-agnostic verifier,
  in-process, bounded — sampling `n = 0 … 2p` and checking the pattern is
  `p`-periodic and non-constant). The toggle was established structurally
  above; what replay guards is the *transport* between the discovery form and
  the input (letter rendering, composition order). Success ⟹ answer
  **NOT_LTL** with the family attached; failure signals corruption, the
  family is discarded, and the answer degrades to **INCONCLUSIVE** — a
  decided answer is never built on unreplayed material.

## 8 — Policy: the screen and the caps

Two policy pieces wrap the construction; neither touches its soundness.

- **The screen.** If the transition monoid of `D` is aperiodic, `L` is
  star-free outright (Thomas 1979: a counter-free deterministic automaton
  whose acceptance is a function of the inf-set recognizes a star-free
  language) — answer **LTL** without building `EM`. The converse fails — a
  group there can be an encoding artefact (layer 10's second example) — so a
  group decides nothing and the pipeline proceeds. The screen is the existing
  GAP aperiodicity oracle; when it cannot run (no GAP, a timeout) it is
  **skipped, not fatal**: the quotient decides regardless. GAP is thereby an
  accelerator on this path, never a dependency.
- **The caps, and the one fence.** Everything the oracle cannot finish takes
  the same exit: the deterministic form unavailable or too many APs for a
  letter set, the closure cap, a time budget, a replay discard — each maps to
  **INCONCLUSIVE** with its own reason, asserting nothing in either
  direction. The fail-safe invariant of the surrounding gate is preserved by
  construction: an absorbing rejection rests only on a replayed family, and
  an LTL answer only on one of the two theorems (screen or quotient).

## 9 — Degenerate cases (no special-casing)

- **Prefix-independent language.** Every residual equals `L`: `≃` has one
  class, `~lin` separates nothing, and the whole decision rides on the
  profiles — the blindness lemma of layer 2, arriving as data, not as a case
  split. Extraction can then only ever produce F₂.
- **Trivial acceptance** (`t`: every run accepts — and dually `f`). Every
  profile is all-true (all-false), `~ω` collapses into `~lin`, and the
  quotient is the residual algebra alone. Universal and empty languages reach
  a one-class quotient: aperiodic, **LTL** — as they should, `true` and
  `false` being formulas.
- **The completion sink.** An absorbing rejecting state is its own residual
  class with an all-false profile row; it is carried through every vector
  like any other slot and never needs a case.
- **The identity element.** Adjoined as element 0 with an empty
  representative; idempotent, so its power cycle has period 1 and the group
  scan skips it by construction.
- **`v` acting without a state cycle.** Nothing in layers 6–7 asks `v`'s
  state action to have an orbit: the periodicity carrier is the *class* power
  cycle. (The evenblocks example below has `v = a` whose action on the
  2-state form is a mere merge–swap; the count lives in the marks.)

## 10 — Worked examples

All three are reproduced by `tests/probes/oracle_dump.py` (one input per
run), which prints exactly the objects below.

### 10.1 — mod-3 counting: the linear shape

`L = a^{3k}·(¬a)^ω` (`samples/fixtures/hoa/various/mod3_a.hoa`). The
deterministic completed form has 5 states (three counter phases, the tail,
the sink) over letters `{a, ¬a}`, acceptance `Inf(0)`.

```
closure     |EM¹| = 15
residuals   5 classes on 5 states (all residuals distinct)
seed        9 classes;  refinement adds nothing:  |S(L)₊¹| = 9
group       v = a,  index a = 1,  period c = 3
chase       b = []          (the seeds of v¹ and v² differ already)
family      F₁:  p = 3,  u = [a],  v = [a],  x = [a; a; cycle{¬a}]
```

The base difference is residual: after one `a` versus two `a`'s the states
disagree on the tail `a·a·(¬a)^ω` — the separator product returns exactly
that lasso. The index absorption puts one `v` into the anchor
(`u = [] + a¹`), and the sample `a·aⁿ·a·a·(¬a)^ω = a^{n+3}(¬a)^ω` toggles
`100 100 …` — period 3, as declared.

### 10.2 — the encoding artefact, resolved: `GF(a ∧ Xa)` in run-parity form

`samples/fixtures/hoa/definability/gf_aa_parity.hoa`: a 2-state deterministic
Büchi recognizer of `GF(a ∧ Xa)` whose letter `a` is a *transposition* — the
transition monoid carries a `Z2`, so the screen reads a group and every
transition-monoid method is stuck with a suspicion at best. The quotient is
not:

```
closure     |EM¹| = 10        (the Z2 is in there)
residuals   1 class on 2 states (the language is prefix-independent)
seed        2 classes;  refined:  |S(L)₊¹| = 6
verdict     aperiodic — LTL
```

The parity words that the transition monoid keeps apart are Arnold-equivalent
— at infinity, modular counts collapse to thresholds — and the quotient
identifies them: ten elements fold to six classes, every power cycle has
period 1, and the answer is a definitive **LTL** where the screen alone could
only abstain forever.

### 10.3 — prefix-independent counting: the ω-power shape

Evenblocks (`samples/fixtures/hoa/definability/evenblocks_nonltl.hoa`):
*infinitely many `¬a`, and eventually every `a`-block has even length* — a
2-state deterministic form with `Fin(0) ∧ Inf(1)`.

```
closure     |EM¹| = 16
residuals   1 class on 2 states  (~lin is blind, as layer 9 predicts)
seed        2 classes;  refined:  |S(L)₊¹| = 7
group       v = a,  index a = 1,  period c = 2
chase       b = [¬a]
family      F₂:  p = 2,  u = [],  v = [a],  y = [a; ¬a]
```

The chase is the part to savor: powers of `a` are indistinguishable to every
residual (one class) and even to the bare profiles — an unfinished `a`-block
has not committed its parity. The BFS finds `b = ¬a`: *close the block*, and
the profiles of `a¹·¬a` and `a²·¬a` disagree. With the index absorbed into
the return word, the family samples `(aⁿ·a·¬a)^ω = (a^{n+1}·¬a)^ω` — blocks
of odd then even length alternating with `n`, period 2. No linear family
exists for this language; the pipeline never needed to know that in advance.

## 11 — Exactness

- **The LTL answer is sound.** Two theorem paths, no heuristic one: the
  screen (transition monoid aperiodic ⟹ star-free, Thomas) and the quotient
  (`EM/~ = S(L)₊` by layers 3–5, aperiodic ⟹ star-free, Perrin). Trust
  asymmetry to note: this answer has no independently checkable certificate —
  it rests on the congruence computation and the residual-equivalence
  primitives being correct. (The natural certificate for LTL would be an
  actual defining formula that verifies; producing one is the surrounding
  project, not this oracle.)
- **The NOT_LTL answer is sound.** Layer 2's soundness is independent of
  everything above it: a replayed toggling family refutes star-freeness on
  its own, whatever produced it. Replay pins the family to the *input*
  automaton, so not even the discovery form is trusted.
- **The decision is complete (up to the caps).** If `L` is not LTL, `S(L)₊`
  has a group; the surjection of layer 3 pulls it back to a group class of
  the quotient, so the scan of layer 6 finds one. Its cycle classes are
  pairwise separated, the chase must terminate (layer 7), the base
  difference exists by definition of the seed, and both assembly branches
  produce a family whose non-constancy is inherited from the chased pair.
  Conversely if `L` is LTL the quotient is aperiodic and the scan exhausts.
  The only exits from this dichotomy are the caps — and each cap exit is an
  explicit INCONCLUSIVE, never a silent wrong answer.

## 12 — Cost

The dominant object is `|EM(D)|`, bounded by `(|Q|·2^{|C|})^{|Q|}` — the
`|Q|` in the exponent is where the explosion lives; the closure cap converts
it into an honest INCONCLUSIVE. Around materialization: the residual classes
cost one language-equivalence product per state × class, once, with no monoid
involved; the profiles cost `O(|EM|·|Q|)`; refinement costs `O(|EM|·|Σ|)` per
split; the chase and the separator are on-demand and touch one pair.
Determinization up front is the unchanged entry toll of every consumer of a
deterministic form.

An opening on the explosion: enriched elements are vectors of `|Q|` slots
over the small local domain `Q × 2^C`, the BFS closure and the refinement are
set-of-vectors fixpoints, and every translation the algorithm uses is a
right-multiplication — which acts on a vector slot-wise. That is the shape
symbolic reachability (decision-diagram sets, fixpoints, level-wise
homomorphisms) is built for; a symbolic `EM` would attack the `|Q|` exponent
directly. Nothing in the congruence or the extraction depends on elements
being enumerated explicitly — only on (a) closure, (b) the per-element seed,
(c) the chase.

## 13 — Architecture

One module per role, each small and autonomous: it owns one algorithmic step
and one data shape, consumes value objects from the modules above it, and can
be exercised alone. The entry point owns **no algorithm** — only sequencing,
caps, and the three-outcome verdict; caps are policy and live there alone, so
every worker is a pure, total function of what it is handed.

```
                 D  (the completed deterministic form)
                      │
       ┌──────────────┴────────────────┐
  residuals.py                     closure.py
  the ~lin base                    the recognizer
       │                               │
       │                          profile.py
       │                          the ~ω seed
       └──────────────┬────────────────┘
                  refine.py
                  the congruence
                      │
                 quotient.py
                  the algebra
                      │
                  family.py
                 the certificate
                      │
                  oracle.py ──► aut2ltl/verifier (replay)
                  the entry
```

- **`enriched.py`** — *the element*: the `(st, mk)` vector value, composition,
  the letter elements, the identity, hashing. A shared primitive of the
  `definability` package rather than of this module.
- **`closure.py`** — *the recognizer* (layer 6.1): BFS under the size budget
  it is handed; the element set, shortest representatives, the right table.
- **`residuals.py`** — *the `~lin` base* (layer 6.2): the state equivalence
  `≃` eagerly, the separator on demand.
- **`profile.py`** — *the `~ω` seed* (layer 6.3): the `A(q, c)` walk and the
  per-element profile.
- **`refine.py`** — *the congruence* (layer 6.4): seed partition,
  right-letter splitting to fixpoint; its second face is the chase (layer 7).
- **`quotient.py`** — *the algebra* (layer 6, tail): class power cycles,
  the aperiodicity verdict, the first group in BFS order.
- **`family.py`** — *the certificate* (layer 7): from the group, the chase
  word and the seed tables to a floor `Witness` of the matching shape; it
  knows nothing of partitions.
- **`oracle.py`** — *the entry* (layer 8), the only impure module: form,
  screen, sequencing, caps, INCONCLUSIVE reasons, replay, verdict.

The data flowing between modules is a handful of small value objects — the
element, the closed monoid, the state classes, the profile table, the class
ids, the group, the `Witness` — so each seam is a typed contract and each
module is testable against fixtures without the ones above it.

**Layering.** Above the floor (`Language`, `Witness`), the letter extractor,
the GAP screen, and the engine-agnostic verifier; imports neither `Cascade`
nor any `Translator`. Consumer: the definability gate, which owns verdict
plumbing (absorbing vs. non-absorbing) around whatever the oracle answers.

## 14 — Peers, literature, out of scope

**Peers.** The sibling `tester/` computes exactly layer 8's screen (and tags
the `Language` so one reading serves the portfolio); the oracle should
consume that cached reading rather than re-run it — a wiring detail. The
sibling `witness/` seeded completion attacks the same negative branch from
one transition-monoid group element; the oracle dominates it on decisiveness
(a seeded search can come home empty on a genuinely non-LTL language — its
`v` is fixed from the wrong monoid — where the quotient cannot), and whether
it also dominates on cost is an A/B on the survey corpora, not an argument.
Until measured, the seeded completion is a candidate cheap first tier on the
suspect branch, nothing more.

**Literature.** The syntactic ω-semigroup and its two-shape congruence are
Arnold (1985); star-free ⟺ aperiodic on ω-words is Perrin (1984), with the
book treatment in Perrin–Pin, *Infinite Words*; the counter-free
deterministic screen is Thomas (1979); the survey chain LTL = FO = star-free
is Diekert–Gastin (2008). The computation itself — quotient a recognizing
monoid by a context congruence via partition refinement — is the classical
syntactic-monoid construction transported to ω-semantics; the collapse of
layer 5 is what makes the transport cheap (a state relation plus a right
congruence, instead of a two-sided refinement over context triples).

**Out of scope (the assembly's concern).**

- **Gate wiring.** Replacing the gate's `PROBABLY_NOT_LTL` decline branch
  with `decide()`, reusing the tester's cached screen, choosing `em_cap`,
  and refreshing the reference CSVs — the recorded TODO item.
- **The cascade is not re-enabled by an LTL answer.** The kr cascade's
  soundness constraint is about its *form* (a counter-free `sbacc`
  automaton), not the language: a proven-LTL language can still present an
  encoding group the holonomy parser misreads. Delegation policy stays with
  the form reading.
- **The symbolic tier.** Layer 12's opening — a decision-diagram `EM` with
  slot-local right-multiplications — is design headroom, deliberately not
  drawn into this construction.
- **Measurement.** Corpus behavior — where `|EM|` lands on the kinska
  counting family, whether the seeded pre-tier ever wins, cap defaults — is
  another session's concern; the construction is validated on the crafted
  fixtures above.
