# The roundtrip algorithm

A translator combinator `roundtrip(Λ, Φ)`, parameterized by a child labeler `Λ` and
a node finder `Φ`. On a language it labels with `Λ`, then replaces the subformula at
one node chosen by `Φ` with an `Λ`-relabeling of that subformula's language.

## Setting

```
Label       =  Some φ  |  ⊥                  -- φ an LTL formula; ⊥ = decline
Translator  =  Language → Label
Λ           :  Translator                    -- the child labeler
Φ           :  Formula → (Node | ⊥)          -- the node finder
```

An LTL formula `φ` is a hash-consed DAG; its **nodes** are its subformula
occurrences. For a node `n` of `φ`:

```
φ↓n         =  the subformula rooted at n
φ[n ↦ ψ]    =  φ with the subformula at n replaced by ψ
               (at every occurrence of the shared node n)
lang(φ)     =  the Language whose ω-language is L(φ)
```

Write `α ≡ β` for ω-equivalence (`L(α) = L(β)`).

## The finder

`Φ` maps a formula to one of its nodes, or declines. Its sole obligation:

```
Φ(φ) = n ≠ ⊥   ⇒   n is a node of φ
```

Nothing further is required of `Φ`.

## The construction

```
roundtrip(Λ, Φ) : Translator
roundtrip(Λ, Φ)(L) =
    case Λ(L) of
      ⊥        →  ⊥
      Some φ   →  case Φ(φ) of
                    ⊥  →  Some φ
                    n  →  case Λ(lang(φ↓n)) of
                            ⊥        →  ⊥
                            Some ψ   →  Some (φ[n ↦ ψ])
```

`Φ` may return any node, including the root (`φ↓n = φ`, the whole formula is
relabeled) or a leaf (`φ↓n` an atom or constant, relabeled to itself); the
construction treats every node uniformly.

## Soundness

`roundtrip(Λ, Φ)` is **faithful-or-`⊥`**: whenever it returns `Some χ`, `χ ≡ L`.

ω-equivalence is a **congruence** for LTL: `w, i ⊨ φ ⇔ w[i:] ∈ L(φ)`, so every
operator depends on its operands only through their ω-languages, and hence
`α ≡ β ⇒ C[α] ≡ C[β]` for every one-hole context `C`. Write `φ = C[φ↓n]` for the
context of the chosen node.

The two formula-emitting exits preserve the language:

- **finder declines** (`Φ(φ) = ⊥`). `Λ` faithful ⇒ `φ ≡ L`; the result is `φ`.
- **relabel succeeds** (`Λ(lang(φ↓n)) = Some ψ`). `Λ` faithful ⇒ `φ ≡ L` and
  `ψ ≡ lang(φ↓n) ≡ φ↓n`. By congruence
  `φ[n ↦ ψ] = C[ψ] ≡ C[φ↓n] = φ ≡ L`.

The two remaining exits — a declined label `Λ(L) = ⊥` and a declined relabel
`Λ(lang(φ↓n)) = ⊥` — return `⊥`. So the only formulas emitted are `Λ`'s own faithful
labels with at most one subformula replaced by an ω-equivalent one; never a
non-faithful formula.
