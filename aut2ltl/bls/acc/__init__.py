"""
aut2ltl.bls.acc — the bounded / transient (X-ladder) cascade-translator member.

`acc` reconstructs cascades whose runs reach a ⊤/⊥ sink within a bounded horizon by
emitting the finite unrolling `Acc(ι)` directly, and declines when a reachable
configuration is recurrent (outside the bounded fragment). Self-contained: it decides
membership by the unroll itself, no external predicate.

Public entry: `acc` (the singleton `CascadeTranslator`). See algorithm.md.
"""
from .acc import Acc, acc

__all__ = ["Acc", "acc"]
