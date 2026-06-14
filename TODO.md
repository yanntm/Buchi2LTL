# aut2ltl — Project TODO

Project-level work items. Engine-level items live in `aut2ltl/kr/TODO.md`.

## Now: cleanup + code review

The construction is correct and the size profile is healthy; we are in a
cleanup pass before a thorough, file-by-file code review. Working mode: walk the
source tree one file at a time, user explains the review point, discuss if
needed, then patch.

LOC inventory of the review surface (`aut2ltl/` source, 6.7k LOC / 33 files):

| file | LOC |
|---|---|
| `kr/reachability_operators.py` | 686 |
| `kr/config_graph.py` | 549 |
| `kr/cascade.py` | 440 |
| `kr/simplify/fold_pass.py` | 427 |
| `kr/ltl_builders.py` | 372 |
| `kr/gap_bridge.py` | 329 |
| `sl/reconstruction.py` | 326 |
| `kr/acceptance_dispatch.py` | 322 |
| `kr/reachability.py` | 320 |
| `sl/reconstruction_helpers.py` | 224 |
| `portfolio/decompose_recombine.py` | 222 |
| `kr/simplify/context_pass.py` | 190 |
| `portfolio/heuristic_gate.py` | 157 |
| `kr/simplify/now_eval.py` | 149 |
| `cli.py` | 141 |
| `sl/invariants.py` | 134 |
| `kr/extract.py` | 132 |
| `kr/simplify/factor_pass.py` | 120 |
| `contract.py` | 102 |
| `kr/fin.py` | 97 |
| `kr/simplify/__init__.py` | 90 |
| `portfolio/sl_driven.py` | 71 |
| `kr/bdd_utils.py` | 65 |
| `kr/__init__.py` | 62 |
| `sl/utils.py` / `sl/__init__.py` | 30 / 26 |
| `portfolio/__init__.py` / `__init__.py` | 23 / 16 |

## Next

- **Real CLI** over `reconstruct_decomposed` (current `cli.py` is an sl-only
  stub). See `STATUS.md` "CLI".
- Engine work items: see `aut2ltl/kr/TODO.md`.
