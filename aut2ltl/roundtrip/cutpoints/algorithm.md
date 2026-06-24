# The cutpoints finders

The finder strategies for `roundtrip`'s `Φ`. Each is a `Finder`; it chooses the node
roundtrip cuts. The brick is sound for any node, so a finder decides only *which*
node — never correctness, only the size of the answer.

## The contract

```
Finder  =  Formula → (Node | ⊥)
```

A `Finder` maps a formula to one of its nodes, or declines (`⊥`). A node is a
subformula occurrence — the `spot.formula` itself, so `φ↓n = n`. Sole obligation:

```
Φ(φ) = n ≠ ⊥   ⇒   n is a node of φ
```

(see `../algorithm.md` for how the brick consumes it). Finders are built lazily, as
cuts call for them; the catalog below is what exists.

## The finders

Write `op(φ)` for the outermost operator of `φ`.

```
root                      -- the whole formula; never declines
root(φ)            =  φ

toplevel(operator)        -- the root iff it carries `operator`
toplevel(operator)(φ)
                   =  φ        if op(φ) = operator
                   =  ⊥        otherwise
```

`root` is the degenerate cut: cutting it relabels the whole formula. `toplevel`
locates the root only when it is of the given kind (e.g. `toplevel(And)`,
`toplevel(Or)`). A finder only *locates* a node; interpreting it — cutting it as-is,
or expanding it to its operands — is the caller's concern, not the finder's.
