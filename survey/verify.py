"""survey.verify — optional spot-oracle equivalence check of a reconstruction.

Decoupled from build: the plain `aut2ltl_survey` run only builds + logs; the
correctness gate turns verification on. Compares the reconstructed formula's
language against the original input in an isolated, bounded spot subprocess
(classify + are_equivalent), reporting a verdict (EQUIV / NON_EQUIV / oracle
timeout / N/A) — a Spot blow-up is reported, never our failure.

Bones only — migrate from tests/survey.py's VERIFY stage, atop survey.bounded.
"""
from __future__ import annotations

# TODO: VerifyResult (verdict, detail)
# TODO: verify(example, build_result, timeout: int) -> VerifyResult
