#!/usr/bin/env python3
"""
Smoke test for aut2ltl.compose (identity + compose) — the decorator-algebra unit
and composition. GAP-free: real Translator/Decorator types, bare spot formulas, no
engine. Decorators wrap the result formula with a unary op so order is observable.

    python3 tests/test_combinators.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spot

from aut2ltl.result import LTLResult
from aut2ltl.compose import compose, identity

_fail = []


def check(cond: bool, msg: str) -> None:
    print(("ok  " if cond else "FAIL") + " : " + msg)
    if not cond:
        _fail.append(msg)


def leaf(_lang):
    """A trivial Translator: always OK with formula `a` (a fresh result each call)."""
    return LTLResult.success(spot.formula("a"), "leaf")


def wrap(op: str):
    """A Decorator: wrap the child result's formula with unary `op` (so composition
    order is visible in the resulting formula)."""
    def deco(child):
        def translator(lang):
            r = child(lang)
            r.formula = spot.formula(f"{op}({r.formula})")
            return r
        return translator
    return deco


G, F, X = wrap("G"), wrap("F"), wrap("X")


def form(t):
    """Run translator `t` and return its formula."""
    return t(None).formula


# --- identity ----------------------------------------------------------------
check(identity(leaf) is leaf, "identity returns its argument unchanged")
check(form(identity(leaf)) == spot.formula("a"), "identity changes no behavior")

# --- compose order (outermost-first) -----------------------------------------
check(form(compose(G, F, X)(leaf)) == spot.formula("G(F(X(a)))"),
      "compose(G, F, X) wraps outermost-first: G(F(X(a)))")

# --- empty compose is identity -----------------------------------------------
check(compose()(leaf) is leaf, "compose() with no decorators is identity")

# --- identity is the unit of compose -----------------------------------------
check(form(compose(G, identity)(leaf)) == form(compose(G)(leaf)) == spot.formula("G(a)"),
      "identity is the unit of compose (compose(G, identity) == compose(G))")

# --- associativity -----------------------------------------------------------
check(form(compose(compose(G, F), X)(leaf))
      == form(compose(G, compose(F, X))(leaf))
      == spot.formula("G(F(X(a)))"),
      "compose is associative")

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s)")
    sys.exit(1)
print("ALL OK")
