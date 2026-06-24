"""
tests/probes/certificate/verify_smoke.py — first prototype of the non-LTL
certificate checker (the *membership* tier).

A non-LTL certificate is a counting family (u, v, x, p): finite words u, v, an
ultimately-periodic tail x (a lasso), and a claimed period p > 1, such that
membership of  u . v^n . x  in the language toggles with  n mod p.

This probe checks such a certificate against an INPUT omega-automaton by
membership ONLY: it asks `u . v^n . x in L` for n = 0..2p via Spot, which judges
membership through automaton intersection and so handles every acceptance type
(Buchi, parity, Rabin, generic Emerson-Lei) uniformly. No internal state is ever
referenced -- the check runs on the automaton the client supplied, which is the
whole point: membership is language-invariant, state indices are not.

THIS IS THE SUGGESTIVE TIER (see research_notes/non_ltl_certificates.md sec 3.2):
finitely many membership samples witness phase *distinguishability* but not yet
*periodicity* (an aperiodic language could mimic the pattern up to any finite n).
The residual-equivalence upgrade that makes it a proof is deferred.

Run from the repo root:
    python3 -m tests.probes.certificate.verify_smoke
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import spot

FIXTURE = "samples/fixtures/hoa/various/parity_a.hoa"


# --------------------------------------------------------------------------- #
# The single load-bearing primitive: membership of a lasso word in L(A).
# --------------------------------------------------------------------------- #
def member(aut: "spot.twa_graph", word: str) -> bool:
    """True iff the ultimately-periodic omega-word `word` is in L(aut).

    Spot decides this by intersecting `aut` with the one-lasso automaton of the
    word; it is correct for any acceptance condition and any (non)determinism.
    """
    w = spot.parse_word(word, aut.get_dict()).as_automaton()
    return aut.intersects(w)


# --------------------------------------------------------------------------- #
# Building the sampled words  u . v^n . x  in Spot's omega-word syntax.
# Words are lists of letter strings, e.g. ["a", "!a"]; x is (prefix, cycle).
# --------------------------------------------------------------------------- #
def _lasso(prefix: List[str], cycle: List[str]) -> str:
    """Render an ultimately-periodic word as Spot syntax: `l; l; cycle{l; l}`."""
    if not cycle:
        raise ValueError("an omega-word needs a non-empty cycle")
    body = "; ".join(prefix + ["cycle{" + "; ".join(cycle) + "}"])
    return body


def _sample_word(u: List[str], v: List[str], n: int,
                 x_prefix: List[str], x_cycle: List[str]) -> str:
    """The word  u . v^n . x  as a lasso string."""
    return _lasso(u + v * n + x_prefix, x_cycle)


# --------------------------------------------------------------------------- #
# The membership-tier verifier.
# --------------------------------------------------------------------------- #
def verify_suggestive(
    aut: "spot.twa_graph",
    u: List[str],
    v: List[str],
    x_prefix: List[str],
    x_cycle: List[str],
    p: int,
) -> Tuple[bool, List[bool]]:
    """Sample membership of u.v^n.x for n = 0..2p and decide whether the pattern
    is non-constant and periodic with period exactly p.

    Returns (ok, pattern). `ok` is True iff the membership pattern toggles (so x
    is phase-sensitive across the v-orbit) AND repeats with period p over the
    sample. This is the SUGGESTIVE verdict, not yet a periodicity proof.
    """
    pattern = [
        member(aut, _sample_word(u, v, n, x_prefix, x_cycle))
        for n in range(2 * p + 1)
    ]
    non_constant = len(set(pattern)) > 1
    periodic = all(pattern[i] == pattern[i + p] for i in range(len(pattern) - p))
    # a smaller period would make the "p" claim wrong (it would really count mod q<p)
    minimal = all(
        not all(pattern[i] == pattern[i + q] for i in range(len(pattern) - q))
        for q in range(1, p)
    )
    return (non_constant and periodic and minimal, pattern)


# --------------------------------------------------------------------------- #
# Smoke run.
# --------------------------------------------------------------------------- #
def _report(title: str, ok: bool, pattern: List[bool], expect: bool) -> bool:
    marks = "".join("1" if b else "0" for b in pattern)
    verdict = "ACCEPT" if ok else "REJECT"
    flag = "OK" if ok == expect else "*** UNEXPECTED ***"
    print(f"  {title:<34} pattern={marks}  -> {verdict}   [{flag}]")
    return ok == expect


def main() -> None:
    aut = spot.automaton(FIXTURE)
    print(f"input automaton: {FIXTURE}  ({aut.num_states()} states, "
          f"acc={aut.get_acceptance()})")

    all_ok = True

    # Genuine certificate: u=eps, v=a, x=(!a)^omega, p=2.
    ok, pat = verify_suggestive(aut, u=[], v=["a"], x_prefix=[], x_cycle=["!a"], p=2)
    all_ok &= _report("genuine (u=eps,v=a,x=(!a)^w,p=2)", ok, pat, expect=True)

    # Tamper 1: non-phase-sensitive tail x=a^omega -> never toggles (all reject).
    ok, pat = verify_suggestive(aut, u=[], v=["a"], x_prefix=[], x_cycle=["a"], p=2)
    all_ok &= _report("tampered x=a^w (not phase-sens)", ok, pat, expect=False)

    # Tamper 2: wrong period claim p=3 on a genuinely period-2 family.
    ok, pat = verify_suggestive(aut, u=[], v=["a"], x_prefix=[], x_cycle=["!a"], p=3)
    all_ok &= _report("wrong period p=3 (real p=2)", ok, pat, expect=False)

    print("SUCCESS" if all_ok else "FAILURE")


if __name__ == "__main__":
    main()
