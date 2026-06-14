#!/usr/bin/env python3
"""
kr/testing/probe_reset_consistency.py

Soundness probe for the parsed cascade: the paper's reachability formulas
(esp. Formula 5 dashed/Enter) are only sound if every combined letter
⟨σ, context⟩ acts on the peeled level's coordinate as IDENTITY or a CONSTANT
(reset). This checks that property on the h-image config dynamics
(casc.move_config), for BOTH context conventions:

  - "lower"  : context = pre[level+1:]  (what _combined_letters_at_level uses)
  - "upper"  : context = pre[:level]    (SgpDec convention: deeper coords
               depend on upper coords)

For each (level, letter, context) it collects the observed map
{pre[level] -> arr[level]} and classifies it: identity / constant / OTHER.
OTHER = the parsed cascade is NOT a reset cascade w.r.t. that convention,
and the operator formulas built on it are unsound (Enter/Stay/Leave keyed
on that context are ambiguous).

Run from project root:
    python3 kr/testing/probe_reset_consistency.py "Ga | Gb"
    python3 kr/testing/probe_reset_consistency.py            # survey set
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import spot

from aut2ltl.kr import decompose_aut


def letter_str(casc, li):
    val = casc.letter_valuations[li]
    return "&".join(("" if v else "!") + k for k, v in sorted(val.items()))


def classify(action: dict) -> str:
    """action: {from_val: to_val} observed. Classify as identity/constant/OTHER."""
    if all(f == t for f, t in action.items()):
        return "identity"
    if len(set(action.values())) == 1:
        return f"reset->{next(iter(action.values()))}"
    return "OTHER " + str(dict(sorted(action.items())))


def probe(fs: str) -> bool:
    f = spot.formula(fs)
    aut = f.translate()
    casc = decompose_aut(aut)
    sizes = [lv.size for lv in casc.levels]
    print(f"--- {fs}: levels={casc.num_levels} sizes={sizes} "
          f"configs={len(casc.all_configs())}")

    ok_all = True
    for level in range(casc.num_levels):
        for conv in ("lower", "upper"):
            bad = []
            # group observed moves by (letter, context)
            obs = {}
            for pre in casc.all_configs():
                for li in range(casc.num_letters()):
                    try:
                        arr = casc.move_config(pre, li)
                    except Exception:
                        continue
                    ctx = pre[level + 1:] if conv == "lower" else pre[:level]
                    obs.setdefault((li, ctx), {})[pre[level]] = arr[level]
            for (li, ctx), action in sorted(obs.items()):
                cls = classify(action)
                if cls.startswith("OTHER"):
                    bad.append((li, ctx, cls))
            status = "OK (reset-consistent)" if not bad else f"{len(bad)} VIOLATIONS"
            print(f"  level {level} context={conv:5s}: {status}")
            for li, ctx, cls in bad[:6]:
                print(f"      letter {letter_str(casc, li):10s} ctx={ctx}: {cls}")
            if bad and conv == "lower":
                ok_all = False
    return ok_all


def main():
    cases = sys.argv[1:] or [
        "Fa", "GFa", "a U b", "Fa | Gb", "Fa & Gb", "Ga | Fb",
        "G(a -> X b)", "Ga | Gb", "F(a & X b)",
    ]
    summary = {}
    for fs in cases:
        try:
            summary[fs] = probe(fs)
        except Exception as e:
            print(f"--- {fs}: ERROR {e}")
            summary[fs] = None
        print()
    print("=== SUMMARY (lower-context convention, the one the operators use) ===")
    for fs, ok in summary.items():
        print(f"  {fs:15s}: {'CONSISTENT' if ok else 'VIOLATED' if ok is False else 'ERROR'}")


if __name__ == "__main__":
    main()
