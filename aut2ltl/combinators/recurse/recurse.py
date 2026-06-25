"""aut2ltl/recurse/recurse.py — the recursive-descent brick (`recurse`).

The structural-recursion combinator that complements `first_success`: where that
one is *choice* (a flat chain of distinct translators), this one is
*self-reference* (a translator that contains itself). See the package README.
"""
from __future__ import annotations

from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from aut2ltl.language import Language
    from aut2ltl.result import LTLResult
    from aut2ltl.translator import Translator


def recurse(step: "Callable[[Translator], Translator]") -> "Translator":
    """Tie a Translator's recursive knot: the least fixpoint of an endofunctor.

    Returns the translator {@code leaf} defined by {@code leaf = step(leaf)} — it
    hands {@code step} a reference to the very translator being built, so that
    {@code step} may delegate sub-problems back to it. This is the one shape every
    decomposing translator shares — decompose the input one level, label each
    strictly-smaller sub-problem the SAME way, recombine — captured once as a
    primitive brick, the recursion complement of {@link first_success}.

    <p>{@code first_success([a, b, c])} is a FLAT chain of distinct translators;
    {@code recurse(step)} is a single translator that refers to ITSELF — the
    self-reference a flat composite cannot express. The two compose: the base case
    of a recursion is just a floor rung of a {@code first_success} inside
    {@code step} (see the usage example below).

    <p><b>Contract of {@code step} (the caller's obligation).</b> {@code step(child)}
    must be a ONE-LEVEL decorator: decompose the input, call {@code child} on each
    resulting sub-problem, recombine the sub-results — and never call {@code child}
    on an input of the same or greater "size". This is exactly the decorator seam
    {@link aut2ltl.daisy.Daisy}, {@link aut2ltl.daisy2.Daisy2} and the
    {@code aut2ltl.decomp} composites already implement: each takes its recursion
    target as a constructor argument.

    <p><b>Termination.</b> {@code recurse} adds NO base case of its own; it is a
    pure knot-tier and contributes no behaviour beyond the self-reference.
    Termination rests entirely on {@code step}'s well-founded descent (every
    delegated sub-problem strictly smaller), and the base case — where nothing
    decomposes — lives inside {@code step}, typically the floor rung of a
    {@code first_success}. A {@code step} that hands back an input no smaller will
    not terminate; that is the caller's obligation, not this brick's.

    <p><b>Soundness.</b> Inherited from the Translator contract: every value that
    flows is an {@link aut2ltl.result.LTLResult} that is language-faithful or
    declined, never wrong. The fixpoint is therefore sound by construction whatever
    {@code step} does.

    <p><b>Usage.</b> A self-flooring peel — try a one-level peel, recurse on its
    exits, and fall to {@code floor} where it does not apply:
    <pre>{@code
    recurse(lambda leaf: first_success([Daisy(leaf), Daisy2(leaf), floor],
                                       name="daisy_pair"))
    }</pre>

    @param step  a Translator endofunctor: given the recursion target as
                 {@code child}, returns a one-level decomposing Translator that
                 delegates strictly-smaller sub-problems to {@code child}.
    @return      the fixpoint Translator {@code leaf} with {@code leaf = step(leaf)}.
    @see aut2ltl.combinators.first_success.first_success  the choice brick this completes.
    """

    def leaf(lang: "Language") -> "LTLResult":
        return step(leaf)(lang)

    return leaf
