# KR Algorithm Description: Translation of Counter-Free Deterministic ω-Regular Automata to LTL via Krohn-Rhodes Cascades

**Core Goal of kr/**: Implement *this* fully systematic, algebraic translation from the Boker–Lehtinen–Sickert FoSSaCS 2022 paper ("On the Translation of Automata to Linear Temporal Logic", full version). 

**No pattern matching**: We explicitly do *not* want ad-hoc heuristics that inspect specific SCC structures, terminal components, "nice" labelings, fusion opportunities, or other shape-based rules on the original automaton (those belong in the separate `buchi2ltl/` engine). Everything must be driven uniformly by the algebraic structure of a Krohn-Rhodes reset cascade (holonomy decomposition) and a recursive syntactic definition of reachability formulas. The only data from the original automaton are the combinatorial objects produced by the decomposition (cascade components, Stay/Leave/Enter partitions of letters per level, configuration mapping).

The paper gives the first *elementary* upper bound: for a counter-free deterministic ω-regular automaton with n states (any acceptance condition), an equivalent LTL formula of **double-exponential temporal nesting depth** and **triple-exponential length**. The construction preserves the acceptance condition in the syntactic future hierarchy of LTL (safety/co-safety fragments etc.).

This file is the canonical "our algorithm description" for the kr/ project. It is a synthesis of detailed algorithmic steps and explanatory motivation/relation to implementation.

## High-Level Algorithm: `TranslateToLTL(D)`

**Input**: Counter-free deterministic ω-regular automaton  
`D = (Σ = 2^{AP}, Q, ι, δ, α)` with |Q| = n (any acceptance condition α, e.g. Müller, Büchi, coBüchi, weak, looping).

**Output**: Equivalent LTL formula ϕ over AP with the complexity and hierarchy guarantees.

1. **Normalize to Müller form** (standard, polynomial time)  
   Obtain an equivalent deterministic Müller automaton D' on the *same* semiautomaton (same Q, ι, δ). Every deterministic ω-regular automaton is equivalent to a Müller one on the identical transition structure.

2. **Krohn-Rhodes-Holonomy reset-cascade decomposition** (Proposition 6 + Eilenberg)  
   Compute a reset cascade (wreath product / hierarchical product)  
   `A = ⟨Σ, A₁, A₂, …, Aₘ⟩`  
   with m ≤ O(n) levels and ≤ O(n) states per level, together with a homomorphism h from the configurations of A to the states of D'.  
   - Each Aᵢ is a simple "reset" semiautomaton.  
   - The cascade is counter-free because D is.  
   - Total configurations of A: at most (O(n))^{O(n)}.  
   Pick any initial configuration ι_A ∈ h⁻¹(ι).

   (In the current kr/ implementation this is performed by `decompose_aut` → SgpDec `HolonomyCascadeSemigroup` → parsed `Cascade` whose `state_to_config` tuples are the configurations and `levels` describe the per-level components. The existing pipeline already produces exactly this representation.)

3. **Lift the acceptance condition to the cascade** (Propositions 7–8)  
   - For Büchi/coBüchi/Rabin: lift directly (preserving the number of pairs for Rabin).  
   - For Müller: obtain an equivalent Müller condition α' on the configurations of A (≤ 2^{O(m n)} accepting sets).  
   - For weak/looping variants: use the special direct constructions (e.g. single sink SCC for looping).

4. **Construct the family of reachability formulas (core inductive construction, Section 4.2)**  
   By induction on cascade level i, define five families of parameterized LTL formulas that express *reachability from configuration S to T while avoiding bad configuration B, under guard β, attaching tail τ when arriving at T*.  
   These distinguish solid-arrow (top-level state unchanged) vs. dashed-arrow (top-level state changes) paths, with strong and weak (dual/release) versions, and ">0" variants that are indifferent to the first letter.  
   See the detailed inductive definition and Table 1 (intended semantics) below. The base case (level 0) is ordinary Until. Higher levels case on source/bad/target equality at the current top level, use disjunctions/conjunctions over Stay(s)/Leave(s)/Enter(t) letters, and recurse to lower-level sub-configurations with adjusted guards (e.g. σ ∧ Xτ, ρ ∧ Xβ).

5. **Encode "visit configuration C only finitely often" (Lemma 7)**  
   For any configuration C of A, define unconditional reachability shorthands:  
   `S ↝ T`   :=  S ~_... T(false)  ▹  T(true)   (main version)  
   `S^{>0} ↝ T` := disjunction over σ of (σ ∧ X (δ(S,σ) ↝ T))   (after first letter)  

   Then:  
   `Fin(C) := ¬(ι_A ↝ C) ∨ ι_A ↝ C ( ¬ (C^{>0} ↝ C) )`  

   `Fin(C) ∈ Σ₂` and holds on w ⇔ the unique run of A on w from ι_A visits C only finitely often.

6. **Assemble the final formula from the (lifted) acceptance condition**  
   For a Müller condition α' on configurations:  
   ϕ = ⋁_{M ∈ α'} ( ⋀_{C ∈ M} ¬Fin(C)  ∧  ⋀_{C ∉ M} Fin(C) )  

   Each disjunct asserts that the set of configurations visited infinitely often is exactly M.  

   For weaker conditions the construction specializes directly (e.g. looping-Büchi becomes a disjunction of reach-to-sink formulas in Σ₁).

7. **(Optional) Finite-word variant (Remark 2)**  
   Replace selected X by the weak next in the "stay-weak" auxiliary; the rest is identical and yields a formula in the corresponding finite-word syntactic fragment.

**Correctness**: By induction on cascade level (Lemma 4) the reachability formulas have the intended semantics w.r.t. cascade runs δ. They stay in the expected syntactic classes (Lemma 5). Fin(C) correctly captures finite visits. The Boolean combination encodes the lifted acceptance. The homomorphism h preserves runs and acceptance. Hence L(D) = L(ϕ).

**Complexity (Lemma 6 + Theorem 2)**:  
- Depth of main reachability formula at level i: ≤ d + 3i (linear in #levels of cascade).  
- Length at level i: singly exponential in i (polynomial factor in |Σ|·n per level).  
- Overall: double-exponential depth (O(2^{O(n)})) and triple-exponential length (2^{2^{O(2n)}}).  
(The cost comes from the number of disjuncts at each level and the recursive blow-up of the change-top-level case.)

## The Five Reachability Formulas (Core Inductive Translation)

Fix a reset cascade A. Configurations of level i are tuples. For state q of level i+1, let Enter(q), Stay(q), Leave(q) be the partitions of combined letters.

For configurations S, B, T of level i and LTL formulas β, τ the five formulas (intended semantics in the paper's Table 1) are defined by induction on i. (Strong versions are co-safety Σ_i; weak are safety Π_i.)

**Formula 1 (main – strong reachability)**:  
S ~_B(β)^X T (τ) :=  
- level 0: (¬β) U τ  
- otherwise: (solid-arrow "stay top" version) ∨ (dashed-arrow "change top" version)  

The solid-arrow version requires the top-level state to remain unchanged throughout (disjunctions over Stay letters + lower-level reachability on sub-configs, with avoidance of bad).  
The dashed-arrow version requires (and accounts for) a change of the top level (using Enter/Leave).

**Formula 2 (weak dual)**:  
The dual/release version of 1: "as long as we have not satisfied the target under τ, we must not hit the bad situation under β".

**Formulas 3 & 4 (stay in top-level state – solid arrow)**:  
Strong (3) and weak (4) versions enforcing that the top component never changes. They case on the four possibilities (source == bad? source == target?) and differ in whether β/τ must hold on the very first letter. The common ">0" sub-formula is a disjunction over σ ∈ Stay(s) of lower-level reachability on the projected sub-configs, conjoined with constraints against leaving s or hitting bad (using the appropriate lower-level formula).

**Formula 5 (change top-level state – dashed arrow, most complex)**:  
Requires seeing a combined letter that enters the new top state t (while avoiding bad), after which the new top is preserved and bad avoided; the path to the entry itself avoided bad (using weak stay); and the top state actually changed (a final disjunct forcing Leave). Uses Formula 4 (weak stay) for part of the avoidance to ensure the overall formula can stay in a co-safety class.

The formulas are mutually recursive; recursion bottoms at level 0 (plain Until). The exact case distinctions appear in the paper (pages 10–13 of the extract). In code they are generated by enumerating Stay/Leave/Enter sets at the current top level (directly computable from the cascade generators / `move_config`) and recursing on projected lower-level configurations.

## Why This Is the "Right" Method for kr/ (No Pattern Matching)

- Everything is driven by the algebraic structure of the cascade (hierarchical reset components produced by holonomy).
- The LTL is generated by a *uniform recursive syntactic translation* whose only inputs are the cascade components, the Stay/Leave/Enter partitions of letters per level, the configuration mapping, and the sub-formulas β/τ.
- The only data used from the *original* automaton are the combinatorial objects from the decomposition. 
- No need (and no desire) to inspect the original automaton for "nice" SCCs, terminal components with mutually exclusive labels, specific entry/exit patterns, fusion opportunities, or other shape-based rules. Those are ad-hoc and incomplete; the cascade already encodes the necessary control flow.
- The cascade view makes "controlled movement between positions while satisfying guards" explicit, which maps directly onto Until/Release/X structure of LTL.
- The main path uses the full inductive definition of the 5 formulas (with their case distinctions on source/bad/target at the current top level, >0 variants, Enter/Leave/Stay disjunctions, and recursion to lower-level sub-configs) for all cascade depths. The recursion bottoms at the paper's level 0 base case (plain Until).

This is the pure, systematic target for the kr/ folder.

## Relation to Current kr/ Implementation

- `Cascade` (cascade.py) provides the cascade representation: `state_to_config` coordinate tuples, `levels`, `letter_valuations`, `move_config`, Enter/Stay/Leave helpers. Config-graph analysis (pruned config automaton, good Muller sets) is in `config_graph.py`.
- `reachability_operators.py` implements the 5 formulas (strong/weak, solid/dashed, >0 variants) uniformly for all depths, bottoming at the level-0 plain-Until base case, plus `fin_c` (Lemma 7).
- `reachability.py` assembles the Muller DNF (`reconstruct_ltl_paper_style`); `reconstruct_bls` is the public per-cascade entry (the Boker-Lehtinen-Sickert construction).
- `decompose_aut` + gap bridge perform the decomposition (stability via `bdd_utils`, parser in `kr/gap/parse.py`).

For current correctness state and remaining work, see `kr/STATUS.md` and `kr/TODO.md` (kept current; this file is the stable spec/motivation). The construction details are in `paper/automata-to-ltl-construction.md`; disputes are settled by `paper/Automata2LTL.txt`.

The size will be large (as predicted by the paper), but the result is elementary, systematic, and free of pattern matching.

## Additional Notes from the Paper

- Unary alphabet warm-up (Section 3) gives *tight* bounds: det → linear, nondet → quadratic, alt → exponential (contrasting with LTL → automata bounds).
- The construction also yields an elementary translation from LTL+past to pure-future LTL (once an elementary bound on determinization to counter-free automata is available).
- No non-linear lower bound is currently known for the general case; closing the gap is open.

(For full proofs, the exact syntactic definitions of Formulas 3–5, Table 2 recurrences, and the unary cases, see the original paper in `paper/Automata2LTL.pdf` (now under version control) or the extracted text `paper/Automata2LTL.txt`. The unary bounds and related work are omitted here for focus on the general case relevant to kr/.)

This is the canonical algorithm description for the kr/ project (the construction we implement directly).