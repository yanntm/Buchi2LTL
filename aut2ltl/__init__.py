"""
aut2ltl — automaton-to-LTL translation: contract, engines, portfolio, CLI.

Root package (P-ARCH, 2026-06-14). Layering, acyclic:

    translator (Translator) + result (LTLResult)   the floor  (CascadeTranslator now in kr)
      ↑
    kr  (pure cascade FoSSaCS engine)   sl  (heuristic engine)
      ↑
    portfolio  (combinators: decompose / gate / sl_driven)
      ↑
    cli / this __init__  (front-end)

The public translate API is re-exported here once `portfolio` lands (campaign
step 5). See bls/TODO.md "THE MOVE CAMPAIGN".
"""
