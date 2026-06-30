# The daisystardet algorithm — the deterministic anchored read-off

A combinator translator that peels a **rejecting SCC with a deterministic
L-partition** and emits a **flat, fixpoint-free, exact** LTL formula, delegating
every exit target to a child. It is the **reachability dual of `partscc`**:
`partscc` labels a *terminal* (escape-free) deterministic SCC with a `G` +
fairness law; daisystardet labels an *exiting, rejecting* deterministic SCC with
the same transition law, but run **`U`-to-an-exit** instead of `G`-with-fairness.

It is the sound, exact replacement for `daisystar`'s flat `LEAVE` (see
[`daisystar/algorithm.md`](../daisystar/algorithm.md)) whenever the phase is
recoverable from the last letter — and, unlike `daisystar`, it is **not restricted
to length-1 stars**: any
rejecting SCC whose entry-letter partition is deterministic qualifies.

## Setting

The Translator/Label contract is unchanged; the translator is parameterized by the
child `Λ` it delegates exit targets to:

```
Label       =  Some φ  |  NotLTL(w)  |  ⊥    -- φ an LTL formula; w a non-LTL witness; ⊥ = decline
Translator  =  Language → Label
```

daisystardet asks the Language for its **TGBA** `A = tgba(L)`, `Σ = 2^AP`. It
applies at the initial SCC `C` (the SCC of `q0 = h`), which has no incoming edge
from outside `C`. For each state `p ∈ C` read off, as in `partscc`:

```
L(p)  =  ⋁ { g : edge (·, g, p) within C }       -- entry label: letters that move into p
O(p)  =  ⋁ { g : edge (p, g, ·) }                -- all out-guards of p (in-C and exits)
exits(p) = { (g, dst) : edge p →(g) dst,  dst ∉ C }
φ_dst =  Λ( of(A↓dst) )                          -- the child label of an exit target
```

## The precondition

daisystardet applies when three local tests hold; it declines otherwise:

1. **`C` is rejecting** (Spot's `is_rejecting_scc`): no accepting run stays in `C`
   forever, so accepting ⟺ leaving `C` — the reachability regime, and `STAY∞` is
   empty.
2. **`C` has at least one exit** (it is *not* terminal — a terminal SCC is
   `partscc`'s job, an exit-free rejecting SCC has empty language).
3. **The L-partition is deterministic**: each `L(p)` is tight (`⊊ true`, non-empty
   except possibly the hub) and the `L(p)` are pairwise disjoint. Disjointness
   makes `A` deterministic on `C`: a letter enters at most one state, so the
   occupied state is a function of the last letter and the run is **unique**.

The third test is the crux — it is exactly `partscc`'s input-determinizing
condition, and it is what removes the phase ambiguity that makes `daisystar`'s flat
`LEAVE` unsound.

## The label

`C` rejecting ⇒ `Final = LEAVE`, and determinism ⇒ a unique run, so the language
is read off by `partscc`'s law carried only *until an exit fires*:

```
law               =  ⋀_{p∈C} ( L(p) → X O(p) )                -- the run stays legal
exit_after_entry  =  ⋁_{p∈C} ⋁_{(g,dst)∈exits(p)} ( L(p) ∧ X(g ∧ X φ_dst) )
exit_at_0         =  ⋁_{(g,dst)∈exits(h)} ( g ∧ X φ_dst )      -- the position-0 hub exit
Final = LEAVE     =  O(h)  ∧  ( exit_at_0  ∨  ( law  U  exit_after_entry ) )
```

- **Anchor `O(h)`.** Position 0 has no incoming letter, so the occupied state is
  fixed to the hub `q0 = h`; the first letter must be a legal move out of `h`.
  This is `partscc`'s `O(q0)` anchor — and exactly what the flat `LEAVE` lacked.
- **Transition law `L(p) → X O(p)`.** Having entered `p` (last letter `∈ L(p)`),
  the next letter is a legal move out of `p`. Determinism makes this *pointwise*
  law equal to *run legality*, step by step — there is no phase to confuse.
- **Exit, anchored at the entering letter.** `exit_after_entry` fires when, having
  entered `p`, the next letter takes an exit edge `g` to `dst`, with the child
  continuation `X φ_dst` after. `exit_at_0` is the same move taken straight from
  the hub at position 0 (no entering letter — covered by the `O(h)` anchor).
- **Strong `U`.** The run *must* reach an exit (consistent with rejecting: it must
  leave `C` to accept). The exit continuation `φ_dst` is `Λ`'s opaque label of
  `A↓dst` — for a true accepting sink, `⊤`.

This is `partscc` with `U exit` in place of `G + ⋀ GF(fairness)`: the same
deterministic transition law, read for *reaching an exit* rather than for *looping
forever fairly*.

### Two readings

- **Two states linked by `X`, each a `U` self-loop, until you exit.** The hub's
  self-loop is its petals, a spoke's is its body; entry/return are the `X`
  connectors; the whole runs as a least-fixpoint to an exit. The deterministic
  law is the flattened form of that fixpoint (phase = last letter).
- **The exit is a cut-copy daisy.** A spoke-exit `E_s ∧ X(G_s U (h_k ∧ X φ_k))` is
  exactly `daisy` applied to a copy of the spoke with its return cut — a pure
  daisy. The final, non-returning excursion is a daisy hanging off the hub.

### Degenerate cases (no special-casing)

- **No spokes / single move**: `law` is vacuous, `LEAVE = O(h) ∧ (σ U EXIT)` — the
  daisy reachability case, `σ` the hub self-loop.
- **A true accepting sink** as a target: `φ_dst = ⊤`, so `… ∧ X ⊤` drops its tail.
  `F(a & X b)` reads off as `1 U (a & X b) ≡ F(a & X b)` — the minimal form.

## Non-LTL exit children (the witness lift)

An exit child `φ_dst = Λ(of(A↓dst))` is three-valued, so it may come back `NotLTL(w)`:
the residue `of(A↓dst)` is not LTL-definable, witnessed by a counting family
`w = (u, v, x, p)` anchored at `dst`. daisystardet propagates the verdict (a non-LTL
exit poisons the peel — absorbing, taken before a decline) and lifts `w` back to `L`'s
initial state.

The lift prepends to the anchor `u` a **reaching word** `w_dst`: one valid path from the
hub `h` to a state `p` carrying an exit to `dst`, followed by that exit guard `g`. Such a
path exists and leads to the suffix `of(A↓dst)`, so `w_dst` reaches `dst` from `h`, and
`w[u ↦ w_dst·u]` re-anchors the family at `h` (`v`, `x`, `p` unchanged).

## Exactness

For a deterministic L-partition the read-off is **exact** (`L(A) = LEAVE`), with no
oracle, by `partscc`'s argument lifted to reachability:

- *Uniqueness.* Disjoint `L(p)` ⇒ each letter enters at most one C-state ⇒ a unique
  run per word inside `C` (until it exits or dies).
- *Completeness.* An accepting run leaves `C` after a finite legal walk; `O(h)`,
  `law`, and the strong `U` to the exit transcribe that walk and its continuation.
- *Soundness.* If `LEAVE` holds, `O(h)` + `law` force a legal deterministic run
  staying in `C` until an actual exit edge fires to `dst` with `φ_dst` after; that
  walk *is* a run of `A`. No standalone body residual can misfire, because the law
  pins the phase at every step — the looseness of
  [`daisystar`'s flat `LEAVE`](../daisystar/algorithm.md) cannot arise.

Confirmed on the flat form's own counterexample
([`tests/fixtures/daisystar_loose.hoa`](../../tests/fixtures/daisystar_loose.hoa)):
the read-off rejects the spurious `c·a·d^ω` (the first letter must be the hub move
`a`, not `c`), where the flat `LEAVE` admitted it.

## Soundness gate (kept as a net) and local validation

Exactness assumes the **deterministic** precondition *and* sound children, so
daisystardet keeps the Spot equivalence gate — to catch an unproven surprise (e.g.
a non-deterministic *exit*) and any child error — and declines on a REJECT
(`DAISYSTARDET_TRACE` prints it). But the whole-formula gate is **fragile**: it
translates `LEAVE` *including the suffix* `φ_dst`, which may be Muller / not
LTL-definable / past Spot's acceptance-set wall — so the gate can reject for a
reason that is **not our peel's fault**.

The fix is to validate **locally**, blind to the suffix:

- *Marker abstraction (sound).* Replace each child sub-automaton `A↓dst` by a fresh
  accepting sink reading a fresh proposition `m_dst` (language `G m_dst`), and
  replace `φ_dst` by `G m_dst` in the candidate. Check equivalence over the
  extended alphabet. This validates the **peel** — reachability *and* routing
  (distinct `m_dst` per target) — independent of the suffix's complexity; the
  suffix's correctness is the child's own (recursive) responsibility. A
  substitution lemma (each `φ_dst ≡ L(A↓dst)`, validated when the child was built)
  then lifts local soundness to the full formula, exactly as a context-free
  production composes.
- *`⊤` abstraction (diagnostic).* Cheaper: set every `φ_dst = ⊤` and redirect every
  exit to one true sink — validates *reachability to some exit* but not routing.
  Useful in the trace to tell a real peel bug (local check fails) from a
  suffix-only gate failure (local passes, whole-formula fails).

## Relation to the family

```
partscc       terminal (escape-free) deterministic SCC   →  O(q0) ∧ G(law) ∧ ⋀GF(fair)
daisystardet  exiting,  rejecting     deterministic SCC   →  O(h)  ∧ (law U exit)
daisystar     rejecting star, ANY L-partition            →  flat LEAVE, gate-rescued
daisy2        recurrence star                              →  STAY∞ ∨ LEAVE (STAY∞ open)
```

daisystardet and `partscc` are the two faces of the deterministic transition law
(loop-forever vs reach-an-exit); `daisystar` is the fallback when the L-partition
is *non*-deterministic (where this read-off declines).

## Out of scope (the assembly's concern)

A genuinely **non-deterministic** rejecting SCC (`L(p) ∧ L(q) ≠ false`) is out of
scope here — adding a fresh proposition to disambiguate the phase is *not* legal
into LTL (projecting it out leaves LTL for QPTL), so daisystardet declines and the
flat `daisystar` (or the cascade) takes it. Whether such a case even arises for an
LTL-definable reachability language is open; the two worked examples and the
benchmark stars are all deterministic. As with the rest of the family, closing the
open recursion with `Λ*`, memoization, and the peel order belong to the assembly,
not this local production.
