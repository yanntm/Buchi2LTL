"""aut2ltl/kanchor — the graded anchored SCC read-off (k-anchor).

Labels the initial SCC of the state-based form when its phase is recoverable
from the last k adjacent letters modulo stuttering, as `STAY∞ ∨ LEAVE` —
exact by construction at every level, exit targets delegated to a child
translator. `algorithm.md` is the reference (`algorithm_k1.md` is the copied
k = 1 document, kept for reconciliation); the package splits as:

* `kanchor.py` — the `KAnchor` combinator Translator (the only export),
  owning the k-ladder (smallest passing level wins).
* `windows.py` — the level-specific trigger-table builders and graded
  precondition tests (the only module that knows what a window is).
* `label.py`   — the level-agnostic assembler `Final = STAY∞ ∨ LEAVE` over a
  `TriggerTable`.
* `pieces.py`  — the letter-level vocabulary (`sojourn`, `leave`, `G L`).
* `shape.py`   — the L/A/M/E split, the P1/P2 test, `reroot` (anchor's copy).
* `lift.py`    — the exact reaching word lifting a NOT_LTL exit witness
  (anchor's copy, level-blind).
"""

from .kanchor import KAnchor

__all__ = ["KAnchor"]
