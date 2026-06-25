"""
aut2ltl.bls.definability.tester — the LTL-definability oracle for a `Language`.

A pure boolean gate: `label_ltl_definable` decides `(definable, conclusive)` and
caches it on the Language (the downstream fail-safe). It knows nothing of witnesses
or of how a NOT_LTL verdict is reported — that orchestration is the gate decorator's
(`bls/definability/gate.py`). See tester.py.
"""

from .tester import label_ltl_definable

__all__ = ["label_ltl_definable"]
