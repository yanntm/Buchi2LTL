# The daisy algorithm

A combinator translator that peels a **single daisy** — the initial state of a TGBA
whose only incoming edges are self-loops — and emits the closed-form LTL of the
language accepted from it, delegating every exit target to a child translator. It is
a **local, context-free production**: it inspects one state's own edges and treats
each target's label as an opaque sub-term supplied by the child. It does not recurse,
and owns no global concern (termination, legal looping, the child's
well-foundedness); those belong to the assembly that wires the child and feeds it
daisies.

## Setting

A translator maps a language to a label; this one is parameterized by the child `Λ`
it delegates exit targets to:

```
Label       =  Some φ  |  NotLTL(w)  |  ⊥    -- φ an LTL formula; w a non-LTL witness; ⊥ = decline
Translator  =  Language → Label
```

daisy asks the Language for its **TGBA** form `A = tgba(L)`,
`A = (Q, Σ, δ, q0, {F_1,…,F_m})`, `Σ = 2^AP`. An edge `(src, g, dst, B)` carries a
Boolean guard `g` (a BDD over `AP`) and the set `B ⊆ {1,…,m}` of acceptance sets it
belongs to. A run is accepting iff for **every** set `i` it takes infinitely many
`i`-marked edges (transition-based generalized Büchi); `m = 0` ⇒ every infinite run
accepts. Transition acceptance is essential: a single state encodes a rich
generalized-Büchi condition — a different petal set per acceptance set — that
state-based marking (all-or-nothing per state) could not express without splitting.

## The daisy

daisy applies only at the **initial state** `q` when `q` is a **daisy**: a center
with **petals** (self-loops `q → q`) and **stems** (exits `q → dst`, `dst ≠ q`), and
**no non-self incoming edge**. That one test — `hasNonSelfIncoming(q)` is false — is
the whole accept/decline boundary: necessary, sufficient, and purely local. It
already guarantees every stem strictly descends (a return path would be a non-self
incoming edge to `q`), so `q` is a singleton SCC and the child labels below are
well-founded.

Split `q`'s out-edges into petals `SL(q)` and stems `EX(q)`, and abbreviate:

```
σ    = ⋁ { g : (g,B) ∈ SL(q) }                       -- all petal guards
σ_i  = ⋁ { g : (g,B) ∈ SL(q), i ∈ B }                -- petals carrying acc set i
φ_j  = Λ( of(A↓dst_j) )                               -- the child label of stem j
```

where `A↓dst` is the sub-automaton rooted at `dst` (reachable-from-`dst`), rewrapped
as a `Language` by `of(·)` — so the child is free to ask it for a *different*
representation, independent of daisy's choice of TGBA.

## The label

A run from `q` either stays on the petals forever or eventually leaves through a
stem; the language is the union (the `∨`):

```
Final(q)  =  STAY∞(q)  ∨  LEAVE(q)
STAY∞(q)  =  G(σ)  ∧  ⋀_{i=1..m} GF(σ_i)              -- stay forever, accepting
LEAVE(q)  =  σ  U  ⋁_j ( g_j ∧ X φ_j )                -- stay finitely, then exit
```

### The three moves

- **Leave** (the right side of the `U`). Take a stem: assert its guard `g_j` now,
  `X φ_j` after. Overlapping stems are just a disjunction — nondeterminism needs no
  determinization.
- **Stay, finitely** (the left side of the `U`). Hold the boolean `σ` and *forget
  acceptance*: a finite stay takes only finitely many petals, so their marks cannot
  help. The **strong** `U` forces an actual exit, after which `φ_j` carries
  acceptance.
- **Stay, infinitely** (`STAY∞`). Assert the TGBA acceptance *restricted to the
  petals*: `G(σ)` lets any petal be taken at each step; `⋀ GF(σ_i)` forces, for each
  acc set, one of its petals infinitely often.

### Degenerate cases (no special-casing)

The single equation already covers the corners:

- **no stems**: the disjunction is empty ⇒ `LEAVE = σ U false = false` ⇒
  `Final = STAY∞`.
- **a petal-unreachable acc set** `i` (`σ_i = false`): `GF(false) = false` ⇒
  `STAY∞ = false` ⇒ `Final = LEAVE` — staying cannot accept, so the run *must*
  leave; the strong `U` drops out on its own (no separate must-leave rule).
- **`m = 0`**: the empty conjunction is `true` ⇒ `STAY∞ = G(σ)`.

## The translator

```
daisy(Λ) : Translator
daisy(Λ)(L) =
    let A = tgba(L); q = init(A) in
    if hasNonSelfIncoming(q) then ⊥                 -- not a daisy (local, N&S)
    else                                            -- q is a daisy
      let φ_j = Λ( of(A↓dst_j) )  for each stem (q, g_j, dst_j, _) ∈ EX(q)
      in if every φ_j = Some ψ_j  then  Some( STAY∞(q) ∨ LEAVE(q, [ψ_j]) )
         else, at the first failing stem k:           -- φ_k ≠ Some, in stem order
              φ_k = ⊥          →  ⊥                    -- cannot label: poisons q
              φ_k = NotLTL(w)  →  NotLTL( w[u ↦ g_k·u] )  -- residue not LTL: lift up the stem
```

It never inspects a child's formula `ψ_j` nor its witness `w` — each exit target is an
opaque sub-label, and the lift `w[u ↦ g_k·u]` prepends one fixed letter without reading
`w`. That is what makes it **context-free**: one local production combining `q`'s own
petals with its children's labels. The first failing stem decides `q`: a decline poisons
it, a non-LTL residue makes it non-LTL.

## Soundness

daisy is **exact on the very-weak (1-weak) fragment** — automata whose only cycles
are self-loops — and declines otherwise, by construction, never by post-hoc
checking. The daisy test guarantees `q`'s single self-reference is the only cycle
through it, resolved in closed form by the stay/leave `U`; the language from `q` is
then `Final(q)` exactly, given correct child labels. Off the fragment a target sits
in a genuine multi-state SCC, the child declines there, and the poisoning propagates
the `⊥` up.

The non-LTL lift is sound for the same reason: the residue `of(A↓dst_j)` is the left
quotient `g_j⁻¹·L` (the stem letter `g_j` is the run's only continuation past `q`), and
star-free `=` LTL is closed under left quotient, so a non-LTL residue forces a non-LTL
`L`. The lifted family certifies it: `g_k·u` reaches from `q` the orbit `u` reached from
`dst_k`, while `v`, `x`, `p` carry over unchanged (re-rooting relocates, it does not
relabel — `Σ = 2^AP` is shared), so `(g_k·u)·vⁿ·x` toggles in `L` exactly as `u·vⁿ·x`
toggles in the residue.

Guards (`σ`, `σ_i`) are symbolic: **no `2^AP` enumeration, no determinization**. Work
and output size scale with states and edges, not the alphabet.

## Out of scope (the assembly's concern)

daisy computes one local label and trusts its inputs. Pushed to the assembly that
drives the labeling: the child `Λ` being well-founded (daisy calls it and trusts the
result); closing the open recursion with a fixpoint `Λ*` and the first-fit dispatch
around it; memoization by state to preserve DAG sharing across daisies; and any
relaxation of the daisy precondition (e.g. stems that loop back, or **daisy chains** —
the big-self-loop direction). Stripping these out is the point: daisy *is* just the
daisy equation.
