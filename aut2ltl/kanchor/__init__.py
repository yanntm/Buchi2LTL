"""aut2ltl/anchor — the anchored SCC read-off.

Labels the initial SCC of the state-based form when its phase is recoverable
from the last anchor letter, as `STAY∞ ∨ LEAVE` — exact by construction, exit
targets delegated to a child translator. `algorithm.md` is the reference; the
package splits as:

* `anchor.py`  — the `Anchor` combinator Translator (the only export).
* `shape.py`   — the L/A/M/E split, the P1/P2 precondition, `reroot`.
* `formula.py` — the read-off `Final = STAY∞ ∨ LEAVE`.
* `lift.py`    — the exact reaching word lifting a NOT_LTL exit witness.
"""

from .anchor import Anchor

__all__ = ["Anchor"]
