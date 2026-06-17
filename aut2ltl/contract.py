"""
aut2ltl/contract.py — DEPRECATED compatibility shim.

`Translator` moved to `aut2ltl.translator` (the contract floor); `CascadeTranslator`
moved to `aut2ltl.bls.cascade_translator` (it is private to the kr engine). This shim
re-exports both so the in-flux portfolio keeps importing from here unchanged; remove
it when the portfolio is reworked.
"""
from aut2ltl.translator import Translator
from aut2ltl.bls.cascade_translator import CascadeTranslator

__all__ = ["Translator", "CascadeTranslator"]
