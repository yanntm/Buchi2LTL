# kr/testing/probe_sgpdec_api.g
#
# API probe for the true-cascade extraction fix (run by hand):
#   gap --no-window --bare kr/testing/probe_sgpdec_api.g
#
# Uses the Ga|Gb normalized-D generators (4 states; letters in comment order)
# and exercises exactly the SgpDec calls the new gap_bridge script will use:
#   SkeletonOf, AsHolonomyCascade, OnCoordinates, AsHolonomyPoint, AsCoords.
# Goal: confirm (a) lifted-generator action on coords differs from the
# AsCoords-of-image shortcut, (b) per-level actions are perm-or-reset,
# (c) AsHolonomyPoint inverts coords -> original point on the closure.

LoadPackage("SgpDec");

gens := [
  Transformation([4,4,4,4]),   # letter !a&!b
  Transformation([4,3,3,4]),   # letter a&!b
  Transformation([1,1,4,4]),   # letter !a&b
  Transformation([1,2,3,4])    # letter a&b
];

T := Semigroup(gens);
hcs := HolonomyCascadeSemigroup(T);
sk := SkeletonOf(hcs);

n := 4;
all_coords := List([1..n], s -> AsHolonomyCoords(s, sk));
Print("STATE_LIFTS: ", all_coords, "\n");
Print("LIFT_INVERTS: ", List([1..n], s -> AsHolonomyPoint(all_coords[s], sk)), "\n");

lifts := List(gens, g -> AsHolonomyCascade(g, sk));
Print("LIFTS_OK: ", Length(lifts), "\n");

# BFS closure of the state lifts under the lifted generators.
visited := ShallowCopy(Set(all_coords));
frontier := ShallowCopy(visited);
while Length(frontier) > 0 do
  c := Remove(frontier);
  for i in [1..Length(lifts)] do
    c2 := OnCoordinates(c, lifts[i]);
    Print("TRANS ", c, " GEN ", i-1, " TO ", c2, "\n");
    if not c2 in visited then
      AddSet(visited, c2);
      Add(frontier, c2);
    fi;
  od;
od;

Print("CLOSURE_SIZE: ", Length(visited), "\n");
for c in visited do
  Print("PI ", c, " POINT ", AsHolonomyPoint(c, sk), "\n");
od;

# Morphism check on the closure: pi(OnCoordinates(c, lift_g)) = delta(pi(c), g).
for c in visited do
  for i in [1..Length(lifts)] do
    c2 := OnCoordinates(c, lifts[i]);
    if AsHolonomyPoint(c2, sk) <> AsHolonomyPoint(c, sk)^gens[i] then
      Print("MORPHISM_FAIL coords ", c, " gen ", i-1, "\n");
    fi;
  od;
od;

Print("PROBE_DONE\n");
QUIT;
