"""
kr/bls.py — DEPRECATED compatibility shim.

The general-case member moved to `aut2ltl.bls.muller` and was renamed `muller` (its
acceptance class), reserving the name `bls` for the construction/engine. This shim
re-exports it under the old names so existing importers and `--use bls` keep working
unchanged; note the technique tag it now reports is `muller`. Remove with the
kr → bls engine rename.
"""
from aut2ltl.bls.muller import muller as bls, Muller as Bls, assemble_muller_dnf

__all__ = ["Bls", "bls", "assemble_muller_dnf"]
