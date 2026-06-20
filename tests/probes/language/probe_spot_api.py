"""Reference: probe the installed spot API used by the Language factory.

Records which cleanup ops exist on twa_graph, which postprocess helpers spot
exposes, whether automata carry any content-hash/canonical form, and whether
spot.formula is a reliable cache key. Kept as a versioned record of what this
build offers (re-run after a spot upgrade). Self-contained (≤15s):

    python3 tests/language/probe_spot_api.py
"""

import spot  # noqa: E402

def main() -> int:
    f = spot.formula("G(a -> X b)")
    a = f.translate()

    print("spot version:", spot.version())
    print("\n--- twa_graph cleanup methods ---")
    for m in ["purge_unreachable_states", "purge_dead_states", "remove_unused_ap",
              "merge_edges", "merge_states", "copy_ap_of"]:
        print(f"  twa_graph.{m:28} {hasattr(a, m)}")

    print("\n--- spot module helpers ---")
    for m in ["canonicalize", "scc_filter", "scc_filter_states", "cleanup_acceptance",
              "reduce_parity", "postprocess", "simplify_acceptance"]:
        print(f"  spot.{m:28} {hasattr(spot, m)}")

    print("\n--- formula as cache key (why we key on str(f), not the object) ---")
    print("  formula == re-parsed:", spot.formula("G(a -> X b)") == f)
    print("  str(formula) stable:", str(spot.formula("G(a -> X b)")) == str(f))

    print("\n--- automata identity/content ---")
    a2 = f.translate()
    print("  two translate() are same object:", a is a2)
    print("  to_str('hoa') stable across translate:", a.to_str("hoa") == a2.to_str("hoa"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
