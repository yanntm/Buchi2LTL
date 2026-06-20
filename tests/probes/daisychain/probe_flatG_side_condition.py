"""Probe: the flat-G STAY-safety form is UNSOUND, in both directions.

aut2ltl/daisy2/algorithm.md considers, for a length-1 star (hub h + one self-loop spoke s), the
tempting flat collapse of the staying language:

    StaySafe  ?=  G( P  v  (G_s U R_s) )      -- the flat form

This probe refutes it. The flat form fails two independent ways:

  * too STRICT at entries, when E_s !|= G_s: the entry position satisfies neither
    P nor G_s U R_s, so the flat G rejects a real staying word;
  * too LOOSE at the hub, ALWAYS: a hub position reading R_s (or a body letter)
    satisfies G_s U R_s with no preceding entry, so the flat G accepts a word with
    no run at all.

The second defect holds even when E_s |= G_s, so neither variant below is
equivalent to the truth -- the only reason G(a->Xb) collapsed to the flat form
was the extra coincidence petal v entry == true (the hub there is never stuck).

Ground truth = the explicit star TGBA with Buchi acceptance on the hub-returning
edges (petal h->h and return s->h), so an accepting run is exactly one that
revisits h infinitely (divergence at s is excluded -- that is decomp/scc's case).
We compare that automaton's language to the flat-G formula, twice; both are
expected NOT equivalent:

  * E_s = e      (entry does NOT imply body) -> flat G too strict AND too loose
  * E_s = e & g  (entry DOES imply body)     -> flat G still too loose at the hub
"""
import spot
import buddy


def star_aut(entry_implies_body: bool) -> "spot.twa_graph":
    """Hub 0, spoke 1.  petal P=p ; entry E=e (or e&g) ; loop G=g ; return R=r.

    Buchi: Inf(0) marks the petal (0->0) and the return (1->0), so accepting
    runs revisit the hub infinitely; looping g^w at state 1 is non-accepting.
    """
    aut = spot.make_twa_graph()
    pv = aut.register_ap("p")
    ev = aut.register_ap("e")
    gv = aut.register_ap("g")
    rv = aut.register_ap("r")
    p = buddy.bdd_ithvar(pv)
    e = buddy.bdd_ithvar(ev)
    g = buddy.bdd_ithvar(gv)
    r = buddy.bdd_ithvar(rv)
    aut.set_acceptance(spot.acc_cond(1, "Inf(0)"))
    aut.new_states(2)
    aut.set_init_state(0)
    acc = [0]
    entry = (e & g) if entry_implies_body else e
    aut.new_edge(0, 0, p, acc)        # petal  (marked: a hub revisit)
    aut.new_edge(0, 1, entry, [])     # entry  h -> s
    aut.new_edge(1, 1, g, [])         # loop   s -> s
    aut.new_edge(1, 0, r, acc)        # return (marked: a hub revisit)
    return aut


def main() -> None:
    flatG = spot.formula("G( p | (g U r) )")
    faut = spot.translate(flatG)
    notG = spot.translate(spot.formula(f"!({flatG})"))
    for label, e_imp_g in (("E !|= G (strict & loose)", False),
                           ("E  |= G (loose at hub) ", True)):
        A = star_aut(e_imp_g)
        eq = spot.are_equivalent(A, faut)          # expected False in both rows
        print(f"{label}: flatG == lang(star)? {eq}   "
              f"{'OK (unsound, as expected)' if not eq else 'UNEXPECTED EQUIV'}")
        strict = A.intersecting_word(notG)         # in lang(star), rejected by flatG
        loose = faut.intersecting_word(spot.complement(A))  # in flatG, no run
        print(f"    too strict (in star \\ flatG) : {strict}")
        print(f"    too loose  (in flatG \\ star) : {loose}")


if __name__ == "__main__":
    main()
