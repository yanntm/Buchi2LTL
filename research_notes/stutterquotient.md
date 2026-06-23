# `stutterquotient`: A Leaf Translator for Stutter-Invariant Deterministic SCCs

## Description

`stutterquotient` is a leaf translator that extends the deterministic L-partition approach of `partscc`/`daisystardet` to **stutter-invariant** automata. It introduces a split of the alphabet into **determining** letters (`d`) that reveal the phase, and **don't-care** letters (`!d`) that preserve the phase until a determining letter appears.

The key insight is that many stutter-invariant LTL formulas (`X`-free) yield automata whose L-partition fails only because of letters that are self-loops on every state (or become so after quotienting). By treating such letters as phase-invisible, we recover a compact, exact LTL read-off where the general cascade would produce an exponentially larger formula.

## Preconditions

The translator applies to an SCC `C` of a deterministic transition-based generalized Büchi automaton (TGBA) satisfying:

1.  **The SCC is a single strongly connected component** (the entire automaton for this leaf translator).
2.  **The SCC is stutter-invariant**: `spot::is_stutter_invariant(aut)` returns `true`.
3.  **There exists a determining alphabet** `D ⊆ Σ` for `C` (see Definition below).

If these conditions hold, `stutterquotient` produces an exact LTL formula for the automaton. Otherwise, it returns `⊥`, deferring to `daisystar` or the general cascade.

## Definitions

### Entry Labels

For each state `s ∈ C`, define:
```
L(s) = { σ ∈ Σ | ∃ t ∈ C . δ(t, σ) = s }
```
i.e., the set of letters that can enter `s` from some predecessor.

### Determining Alphabet

A subset `D ⊆ Σ` is a **determining alphabet** for SCC `C` if:

1.  **Deterministic entry on `D`**: The sets `L(s) ∩ D` form a partition of `D`. That is:
    - For all `s ≠ t`, `(L(s) ∩ D) ∩ (L(t) ∩ D) = ∅`
    - `⋃_{s ∈ C} (L(s) ∩ D) = D`

2.  **Phase preservation on `!D`**: For every state `s ∈ C`, the following LTL law holds:
    ```
    G( L(s) -> ( (!D -> X L(s)) W D ) )
    ```
    This says: once a letter enters state `s`, the automaton remains in phase `s` through all don't-care letters (`!D`) until a determining letter (`D`) appears. If no determining letter ever appears, the condition holds weakly.

### Quotient Transition Law

Let `O(s)` be the set of letters that can **start** from state `s` (including both `D` and `!D` letters):
```
O(s) = { σ ∈ Σ | δ(q₀, σ) = s }
```

The **quotient transition law** on `D` is:
```
law_D = ⋀_{s ∈ C} ( (L(s) ∧ D) -> X O(s) )
```
This says: if the current letter is in `L(s) ∩ D` (i.e., it is a determining letter entering `s`), then the next letter must be startable from `s`.

### Exit and Fairness

Let:
```
Exit = { σ ∈ D | ∃ s ∈ C . δ(s, σ) ∉ C }
```
be the set of determining letters that leave the SCC.

Let:
```
Fair = { F_i | F_i ∩ C ≠ ∅ }
```
be the accepting sets that intersect the SCC.

## Algorithm

Given an SCC `C` with initial state `q₀` and acceptance sets `{F₁, ..., Fₖ}`:

**Step 1: Check stutter-invariance.**  
If `spot::is_stutter_invariant(aut)` returns `false`, return `⊥`.

**Step 2: Find a maximal determining alphabet `D ⊆ Σ`.**  
This is a search over subsets of the alphabet (or a heuristic based on the L-partition). For each candidate `D`:
- Verify that `L(s) ∩ D` forms a partition of `D`.
- Verify that `G( L(s) -> ( (!D -> X L(s)) W D ) )` holds for all `s ∈ C`.

If no such `D` exists, return `⊥`.

**Step 3: Build the quotient transition law.**  
Compute `law_D` as defined above.

**Step 4: Determine the regime (staying vs. leaving).**  
If `Exit = ∅` (terminal SCC), the `U`-branch is false.  
If `Fair = ∅` (rejecting SCC), the `G`-branch is false.  
If both are non-empty, both branches are possible.

**Step 5: Construct the formula.**

The generalized deterministic SCC formula is:
```
O(q₀) ∧ ( (law_D U (Exit ∧ φ_child)) ∨ ( G(law_D) ∧ ⋀_{F ∈ Fair} GF( ⋁_{s ∈ F} L(s) ) ) )
```

Where:
- `φ_child` is the formula of the target SCC reached on exit (provided by the assembler).
- If `Exit = ∅`, the `U`-branch is `false`.
- If `Fair = ∅`, the `G`-branch is `false`.

**Step 6: Return the formula.**

## Correctness Argument

**Lemma 1 (Phase preservation):**  
Let `D` be a determining alphabet for `C`. The law:
```
G( L(s) -> ( (!D -> X L(s)) W D ) )
```
ensures that for any infinite word, if the automaton is in phase `s` (i.e., the current letter enters `s`), then all subsequent letters from `!D` preserve that phase until a `D` letter occurs. If no `D` letter ever occurs, the phase remains `s` forever (weak until vacuously).

**Lemma 2 (Quotient transition law is exact on `D`):**  
On the subsequence of letters from `D`, the entry labels `L(s) ∩ D` form a deterministic partition. Therefore, the transition law:
```
G( ⋀_s ( (L(s) ∧ D) -> X O(s) ) )
```
is an exact characterisation of the phase evolution on the `D`-subsequence.

**Theorem (Correctness of `stutterquotient`):**  
Let `aut` be a deterministic TGBA satisfying the preconditions. Let `φ` be the formula produced by Step 5. Then `L(φ) = L(aut)`.

*Proof sketch:* By stutter-invariance (precondition) and Lemma 1, letters from `!D` can be ignored in the sense that they do not change the phase. Lemma 2 gives the exact transition law on the `D`-subsequence. The `U` branch captures exactly the runs that eventually leave the SCC on a `D` letter, and the `G` branch captures exactly the runs that stay forever and satisfy the fairness condition. The `∨` is exhaustive, and the two branches are mutually exclusive on the `D`-subsequence. The `O(q₀)` anchor ensures the first letter is valid. Thus the formula is semantically equivalent to the automaton. ∎

## Example: `G(!a | Fb)`

Consider the automaton for `G(!a | Fb)`:

- States: `{0, 1}`, initial `0`
- Accepting: `{0}` (Büchi)
- Transitions:
  - State 0: `!a ∨ b` → 0 (accepting), `a ∧ !b` → 1
  - State 1: `b` → 0 (accepting), `!b` → 1

The L-partition is:
- `L(0) = !a ∨ b`
- `L(1) = !b`

These overlap on `!a ∧ !b` (a self-loop on both states). The standard deterministic L-partition fails.

`stutterquotient` finds:
- `D = { b, a ∧ !b }` (the letters that change phase)
- `!D = { !a ∧ !b }` (the universal self-loop)

The phase-preservation law holds trivially: `!D` is a self-loop on both states.

The quotient law is:
```
law_D = ( b -> X ( !a ∨ b ) ) ∧ ( (a ∧ !b) -> X !b )
```

Since the SCC is rejecting (`Fair = ∅`), the formula is:
```
O(0) ∧ ( law_D U Exit )
```
where `Exit = { b }` (leaves state 1 to state 0).

This simplifies to:
```
G( (a ∧ !b) -> F b )
```
which is equivalent to `G(!a | Fb)`.

## Complexity

- **Stutter-invariance check:** `O(|C|^2 * |Σ|)` (Spot implementation).
- **Determining alphabet search:** Exponential in `|Σ|` in the worst case, but in practice a greedy heuristic (maximal self-loop set) suffices.
- **Formula size:** Linear in `|C|` and `|D|` (after BDD simplification), avoiding the exponential blowup of the general cascade.

## Discussion

### Relationship to `partscc` and `daisystardet`

If `D = Σ` (all letters are determining), the phase-preservation law is vacuous (`!D = ∅`), and the quotient reduces to the standard L-partition. In this case, `stutterquotient` specializes to `partscc`/`daisystardet`. Thus `stutterquotient` is a strict generalization for stutter-invariant automata.

### When It Fails

The translator returns `⊥` if:
- The SCC is not stutter-invariant (Spot's `is_stutter_invariant` returns `false`).
- No determining alphabet `D` exists.
- The SCC is not a single SCC (handled by the assembler).

In such cases, the tool falls back to `daisystar` or the general cascade.

### Limitations and Future Work

- The search for a maximal `D` is combinatorial. A practical implementation may use the stutter quotient of the automaton to identify `D` automatically.
- The current formulation assumes a deterministic TGBA. Extending to non-deterministic automata would require a different approach (e.g., subset construction).

## References & Comments

- Stutter-invariance check uses `spot::is_stutter_invariant(aut)` (Spot library).
- The `W`-based phase-preservation law was developed in collaboration with DeepSeek (2025–2026). The key innovation is the explicit split of the alphabet into determining and don't-care letters, with the weak until operator capturing the phase-preservation invariant.


v0 : 

# `stutterquotient`: A Stutter-Quotienting Leaf Translator for Deterministic SCCs

## Description

`stutterquotient` is a leaf translator that extends the deterministic L-partition approach of `partscc`/`daisystardet` to automata whose L-partition fails **solely due to universal stuttering letters**—letters that act as self-loops on every state of the SCC.

The insight is simple: if a letter does not change the state, its occurrences can be ignored when determining the phase sequence. The language is stutter-invariant (equiv. `X`-free LTL), so deleting or inserting such letters does not affect membership. After quotienting out these universal stuttering letters, the remaining L-partition often becomes deterministic, enabling a compact, exact read-off where the general fallback would produce an exponentially larger formula.

## Preconditions

The translator applies to an SCC `C` of a deterministic transition-based generalized Büchi automaton (TGBA) satisfying:

1.  **The SCC is a single strongly connected component** (the entire automaton for this leaf translator).
2.  **The SCC is stutter-invariant**: `spot::is_stutter_invariant(aut)` returns `true`.
3.  **The L-partition after stutter-quotienting is deterministic** (see Definition 2 below).

If these conditions hold, `stutterquotient` produces an exact LTL formula for the automaton. Otherwise, it returns `⊥`, deferring to `daisystar` or the general cascade.

## Key Concepts

### Deterministic L-Partition (Standard)

For each state `s`, define:
```
L(s) = { σ ∈ Σ | ∃ t. δ(t, σ) = s }
```
i.e., the set of letters that can enter `s` from some predecessor.

The family `{ L(s) }` is a **deterministic partition** if:
- For all `s ≠ t`, `L(s) ∩ L(t) = ∅`
- `⋃_s L(s) = Σ` (it is a partition of the alphabet)

This partition is the pre-condition for `partscc` and `daisystardet`.

### Universal Stuttering Letters

A letter `τ ∈ Σ` is a **universal stuttering letter** (or **stutter letter**) for SCC `C` if:
```
∀ s ∈ C . δ(s, τ) = s
```
That is, `τ` is a self-loop on every state of the SCC. Let:
```
Σ_τ = { τ | ∀ s ∈ C . δ(s, τ) = s }
```

### Quotient L-Partition

Remove the stutter letters from the entry labels:
```
L_τ(s) = L(s) \ Σ_τ
```

The quotient L-partition is **deterministic** if `{ L_τ(s) }` forms a partition of `Σ \ Σ_τ`.

## Algorithm

Given an SCC `C` with initial state `q₀` and acceptance sets `{F₁, ..., Fₖ}`:

**Step 1: Compute universal stutter letters.**
```
Σ_τ = { σ | ∀ s ∈ C . δ(s, σ) = s }
```

If `Σ_τ = ∅` and the standard L-partition is already deterministic, defer to `partscc`/`daisystardet`.

**Step 2: Compute quotient entry labels.**
```
L_τ(s) = { σ | σ ∉ Σ_τ and ∃ t ∈ C . δ(t, σ) = s }
```

If `{ L_τ(s) }` is not a partition of `Σ \ Σ_τ`, return `⊥`.

**Step 3: Build the quotient transition law on the reduced alphabet.**
For each state `s`, define:
```
O(s) = { σ | σ ∉ Σ_τ and δ(q₀, σ) = s }
        ∪ { τ | τ ∈ Σ_τ }
```
In practice, `O(s)` is the set of letters that can **start** from state `s` (including stutter letters).

The quotient transition law is:
```
law = ⋀_{s ∈ C} ( L_τ(s) → X O(s) )
```
This says: if the current letter is in `L_τ(s)`, then the next letter must be startable from `s`.

**Step 4: Determine the regime (staying vs. leaving).**

Let `Exit` be the set of quotient letters that leave the SCC:
```
Exit = { σ | σ ∉ Σ_τ and ∃ s ∈ C . δ(s, σ) ∉ C }
```

Let `Fair` be the acceptance sets for runs that stay in the SCC forever (relative to the quotient):
```
Fair = { F_i | ∃ s ∈ F_i ∩ C }
```

**Step 5: Construct the formula.**

The generalized deterministic SCC formula is:
```
O(q₀) ∧ ( (law U (Exit ∧ φ_child)) ∨ ( G(law) ∧ ⋀_{F ∈ Fair} GF( ⋁_{s ∈ F} L_τ(s) ) ) )
```

Where:
- `φ_child` is the formula of the target SCC reached on exit (provided by the assembler).
- If `Exit = ∅` (terminal SCC), the `U`-branch is false, yielding the `partscc` formula.
- If `Fair = ∅` (rejecting SCC), the `G`-branch is false, yielding the `daisystardet` formula.
- If both are non-empty (accepting with exits), the `∨` captures both behaviors.

**Step 6: Return the formula.**

## Correctness Argument

**Lemma 1 (Stutter deletion preserves acceptance):**  
Let `w ∈ Σ^ω` and let `w'` be obtained by deleting all occurrences of letters from `Σ_τ`. Because every `τ ∈ Σ_τ` is a self-loop on every state, the sequence of states visited by the automaton on `w` and `w'` differs only in the number of consecutive repetitions of the same state. Since the language is stutter-invariant (precondition), `w ∈ L(aut)` iff `w' ∈ L(aut)`.

**Lemma 2 (Quotient law is exact):**  
On the reduced alphabet `Σ \ Σ_τ`, the entry labels `L_τ(s)` form a deterministic partition. Therefore, the transition law:
```
G( ⋀_s ( L_τ(s) → X O(s) ) )
```
is an exact characterisation of the phase evolution on the reduced alphabet.

**Theorem (Correctness of `stutterquotient`):**  
Let `aut` be a deterministic TGBA satisfying the preconditions. Let `φ` be the formula produced by Step 5. Then `L(φ) = L(aut)`.

*Proof sketch:* By Lemma 1, it suffices to show the formula is exact on the reduced alphabet. Lemma 2 gives the exact transition law. The `U` branch captures exactly the runs that eventually leave the SCC, and the `G` branch captures exactly the runs that stay forever and satisfy the fairness condition. The `∨` is exhaustive, and the two branches are mutually exclusive on the reduced alphabet. The `O(q₀)` anchor ensures the first letter is valid. Thus the formula is semantically equivalent to the automaton. ∎

## Complexity

- **Stutter letter computation:** `O(|C| * |Σ|)` time.
- **L-partition construction:** `O(|C| * |Σ|)` time.
- **Formula size:** Linear in `|C|` and `|Σ|` (after BDD simplification), avoiding the exponential blowup of the general cascade.

## Discussion

### Relationship to `partscc` and `daisystardet`

`stutterquotient` generalizes both translators by treating stutter letters as phase-invisible. If `Σ_τ = ∅`, the quotient reduces to the standard L-partition, and the algorithm specializes to the existing deterministic cases. Thus `stutterquotient` is a strict superset of `partscc`/`daisystardet` for stutter-invariant languages.

### When It Fails

The translator returns `⊥` if:
- The SCC is not stutter-invariant (Spot's `is_stutter_invariant` returns `false`).
- The quotient L-partition remains non-deterministic.
- The SCC is not a single SCC (handled by the assembler).

In such cases, the tool falls back to `daisystar` or the general cascade.

### Practical Impact

Many real-world LTL specifications are stutter-invariant (e.g., response, fairness, persistence). The automata for these formulas often have universal stutter letters that break the deterministic L-partition. `stutterquotient` recovers the exact compact read-off, significantly reducing formula size and translation time for this common class of properties.

## References & Comments

- The stutter-invariance check uses `spot::is_stutter_invariant(aut)` (Spot library).
- The quotienting idea was developed in collaboration with DeepSeek (2025-2026). The key insight is that universal stuttering letters are phase-invisible and can be safely projected out, reducing the problem to the deterministic L-partition case.

---

*This document describes a new leaf translator proposed for integration into `aut2ltl`. It fills the gap between the deterministic fragment (`partscc`/`daisystardet`) and the general fallback, providing exact, compact LTL reconstruction for a practically significant class of stutter-invariant automata.*
