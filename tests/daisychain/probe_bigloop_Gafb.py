"""Brainstorm probe: does the big-self-loop daisy design reproduce G(a|Fb) cleanly?

Checks the hand-derived chain for the 0<->1 SCC:
  detour folded by sl        -> (!b U b)
  generalized STAY at hub 0  -> G( (a|b) | (!a & !b & (!b U b)) )
  target (the input)         -> G(a | Fb)
all three "stay" forms should be language-equivalent.
"""
import spot

def equiv(x: str, y: str) -> bool:
    fx, fy = spot.formula(x), spot.formula(y)
    return spot.are_equivalent(fx, fy)

target   = "G(a | Fb)"
detour   = "!b U b"                                  # sl on the detour sub-aut
recon    = f"G( (a|b) | (!a & !b & ({detour})) )"    # generalized STAY at the hub

print("detour folds to Fb     :", equiv(detour, "Fb"))
print("recon  == target       :", equiv(recon, target))
print("recon                  :", spot.formula(recon))
print("recon simplified       :", spot.simplify(spot.formula(recon)))
