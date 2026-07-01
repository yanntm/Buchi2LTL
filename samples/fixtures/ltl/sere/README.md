# fixtures/ltl/sere — SERE/PSL inputs

SERE (the regular-expression sublanguage of PSL) mixed with LTL operators, fed
in as formulas and reconstructed back to LTL. A side-effect corpus: the front
end accepts PSL, so these ride the same formula → automaton → LTL path as any
LTL input. Groups, kept as `#` section comments in `sere.ltl`:

- **bounded SERE** — finite `;`-concatenations (`{a;b;c}`, `{a[+]}|->b`), the
  clean nested-`X` corner.
- **SERE under an LTL temporal context** — a SERE trigger wrapped in `F`/`U`.
- **SERE fusion / boolean operators** — fusion `:` and the suffix implications
  `|->` / `[]->` meeting LTL.
- **GF/FG over short SEREs** — recurrence / persistence of a small pattern over
  a few letters.
- **modular counting** — SEREs whose language is *not* LTL-definable (`{(a;a)[*]}`
  counts mod 2); these decide `NOT_LTL` with a checkable counting-family witness.
- **a single dense recurrent SCC** — a `G`-closed pattern whose automaton is one
  monolithic SCC (identical to the plain-LTL form `G((a & Xb & XXc) -> XXXd)`);
  the SCC/peel decompositions can't split it. Not a SERE issue — a hard corner of
  the reconstruction path, kept as a marker.
