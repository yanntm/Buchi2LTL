#!/usr/bin/env python3
"""
Visualization helper for the size-2 fusion heuristic.

Generates GraphViz DOT and PNG renderings of the automaton
before and after the absorption transformation.

Usage:
    python3 testing/visualize_fusion.py "X(p1 | F(p1 & Xp1))"

If no formula is given, it uses the classic running example.
"""

import sys
import subprocess
import os
from pathlib import Path

import spot

# Make sure we can import from the project
sys.path.insert(0, str(Path(__file__).parent.parent))

from testing.fusion_heuristic_v2 import try_absorb_size2_v2


def aut_to_dot(aut, title=""):
    """Return a DOT string for the automaton, with an optional title."""
    dot = aut.to_str("dot")
    if title:
        # Inject a label into the digraph line
        dot = dot.replace("digraph G {", f'digraph G {{\n  label="{title}";\n  labelloc=top;')
    return dot


def render_dot(dot_text: str, output_path: Path):
    """Write DOT to file and render to PNG using Graphviz."""
    dot_path = output_path.with_suffix(".dot")
    png_path = output_path.with_suffix(".png")

    dot_path.write_text(dot_text)

    try:
        subprocess.run(
            ["dot", "-Tpng", "-o", str(png_path), str(dot_path)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"  Rendered: {png_path}")
    except subprocess.CalledProcessError as e:
        print(f"  Failed to render PNG: {e.stderr}")
        print(f"  DOT file saved at: {dot_path}")
        png_path = None

    return png_path


def main():
    formula = sys.argv[1] if len(sys.argv) > 1 else "X(p1 | F(p1 & Xp1))"

    print(f"Visualizing fusion heuristic on: {formula}")
    print("=" * 70)

    out_dir = Path("testing/debug_images")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_name = formula.replace(" ", "_").replace("|", "or").replace("&", "and").replace("!", "not")[:60]

    # === Original automaton ===
    print("\n[1] Original automaton")
    aut = spot.formula(formula).translate("GeneralizedBuchi", "Small", "High")
    print(f"    States: {aut.num_states()}, Acceptance: {aut.get_acceptance()}")

    dot_orig = aut_to_dot(aut, title=f"Original: {formula}")
    png_orig = render_dot(dot_orig, out_dir / f"before_{safe_name}")

    # Show SCC info
    si = spot.scc_info(aut)
    print("    SCCs:")
    for i in range(si.scc_count()):
        states = list(si.states_of(i))
        print(f"      SCC {i}: states={states}, accepting={si.is_accepting_scc(i)}")

    # === Run the fusion heuristic ===
    print("\n[2] Running fusion heuristic (v2)")
    massaged = try_absorb_size2_v2(aut)

    if massaged is None:
        print("    Heuristic returned None (no transformation applied or failed)")
        print("    Nothing to visualize for 'after'.")
        return

    print(f"    Transformed automaton has {massaged.num_states()} states")

    dot_after = aut_to_dot(massaged, title=f"After fusion: {formula}")
    png_after = render_dot(dot_after, out_dir / f"after_{safe_name}")

    # Show SCCs after
    si2 = spot.scc_info(massaged)
    print("    SCCs after transformation:")
    for i in range(si2.scc_count()):
        states = list(si2.states_of(i))
        print(f"      SCC {i}: states={states}, accepting={si2.is_accepting_scc(i)}")

    # Equivalence check
    try:
        eq = spot.are_equivalent(aut, massaged)
        print(f"\n    Language equivalent to original? {eq}")
    except Exception as e:
        print(f"    Equivalence check failed: {e}")

    print("\n=== Generated files ===")
    if png_orig:
        print(f"  Original PNG: {png_orig}")
    print(f"  Original DOT: {out_dir / f'before_{safe_name}.dot'}")
    if png_after:
        print(f"  After PNG:    {png_after}")
    print(f"  After DOT:    {out_dir / f'after_{safe_name}.dot'}")


if __name__ == "__main__":
    main()
