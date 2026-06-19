"""
bls/options.py — the kr engine's OPTIONS contract.

The COMPLETE, discoverable contract of every `os.environ` knob the kr package
reads: each is declared as an `OptionSpec` (dotted key + native default + one-line
doc + the legacy `env` var). `OptionSpec` is documentation AND the single default
source, so this module is where "what can be configured in kr" lives — regardless
of whether a given knob is threaded as instance config yet.

Declaration vs. wiring (see TODO "Configurability"):
- **Bucket 1 — wired now** (`kr.dispatch.*`): read at construction via
  `options.get(SPEC)` (in `make_hierarchy_class`). `KR_DISPATCH_OPTIONS` is the
  sub-list the portfolio builder threads into the shared `Options`.
- **Bucket 2 — declared, call site still on env:** real A/B optimization knobs,
  but pervasive in the recursive core / simplifier; promoted only if per-instance
  optimization A/B is ever needed.
- **Bucket 3 — declared, call site stays on env:** tracing + resource/safety
  limits — process-wide scope is correct; the spec just documents them.

Each `default` MIRRORS the current in-code default; until a call site is repointed
it keeps reading `os.environ` directly, so the spec and the code must agree. NOTE:
the floor's bool `_coerce` is `value != "0"` (matches the Bucket-1 dispatch
convention exactly); the Bucket-2/3 bools use the richer `not in {0,false,no,off}`
convention at their own call sites — reconcile when/if those are repointed.

`KR_SAT_MIN_STATES` is read in the floor `aut2ltl/language.py`, not kr, so it is
declared in `aut2ltl/language` (its own OPTIONS contract), not here.
"""
from __future__ import annotations

from aut2ltl.options import OptionSpec

# --- Bucket 1: acceptance-dispatch chain membership (bls/hierarchy_class.py) ---
# Which acceptance-class leaves enter the dispatch chain. Read at BUILD time when
# the chain is assembled (not per-call). Weak is OFF by default (correct, but a
# size regression vs buchi/cobuchi). These are the knobs wired to Options now.

DISPATCH_ACC = OptionSpec(
    "kr.dispatch.acc", True,
    "include the Acc(c) bounded-fragment leaf in the dispatch chain",
    env="KR_DISPATCH_ACC")

DISPATCH_WEAK = OptionSpec(
    "kr.dispatch.weak", False,
    "include the weak/looping leaf (off by default: correct but larger)",
    env="KR_DISPATCH_WEAK")

DISPATCH_BUCHI = OptionSpec(
    "kr.dispatch.buchi", True,
    "include the Buchi (recurrence) leaf in the dispatch chain",
    env="KR_DISPATCH_BUCHI")

DISPATCH_COBUCHI = OptionSpec(
    "kr.dispatch.cobuchi", True,
    "include the coBuchi (persistence) leaf in the dispatch chain",
    env="KR_DISPATCH_COBUCHI")

# --- Bucket 2: sound optimization A/B knobs (declared; call sites still on env) ---

FOLD_FIN_REACH = OptionSpec(
    "kr.fold_fin_reach", True,
    "per-conjunct Fin-reachability fold (drop Fin(C) for C unreachable from M)",
    env="KR_FOLD_FIN_REACH")

FUSE_LETTERS = OptionSpec(
    "kr.fuse_letters", True,
    "letter fusion: one summand per outcome class (Minato-minimized guard OR)",
    env="KR_FUSE_LETTERS")

SIMP_OWN = OptionSpec(
    "kr.simp.own", True,
    "run the own simplify pipeline (context/now-eval/factor/subsumption rules)",
    env="KR_SIMP_OWN")

SIMP_OWN_FOLD = OptionSpec(
    "kr.simp.own_fold", True,
    "own simplify rule 4: unroll-inverse folds (shrinks the distinct-temporal census)",
    env="KR_SIMP_OWN_FOLD")

SIMP_OWN_FACTOR = OptionSpec(
    "kr.simp.own_factor", True,
    "own simplify rule 3: partial factoring (off = rules 1+2 only)",
    env="KR_SIMP_OWN_FACTOR")

# --- Bucket 3: tracing + resource/safety limits (declared; stay on env) ---

TRACE = OptionSpec(
    "kr.trace", False,
    "emit [KR] construction trace lines",
    env="KR_TRACE")

REACH_GUARD = OptionSpec(
    "kr.reach_guard", 5_000_000,
    "abort after this many DISTINCT reach_strong subproblems (runaway guard)",
    env="KR_REACH_GUARD")

MAX_LEVELS = OptionSpec(
    "kr.max_levels", 0,
    "opt-in cascade depth ceiling (0 = no ceiling)",
    env="KR_MAX_LEVELS")

FLATTEN_TREE_LIMIT = OptionSpec(
    "kr.flatten_tree_limit", 250_000,
    "max unfolded-tree size to flatten the DAG to a string (output path only)",
    env="KR_FLATTEN_TREE_LIMIT")

SIMP_NODE = OptionSpec(
    "kr.simp.node", True,
    "run Spot's per-node simplifier during assembly",
    env="KR_SIMP_NODE")

SIMP_TREE_LIMIT = OptionSpec(
    "kr.simp.tree_limit", 0,
    "per-node simplify size gate (0 = always; <0 = historical always-simplify)",
    env="KR_SIMP_TREE_LIMIT")

SIMP_OPTS = OptionSpec(
    "kr.simp.opts", "hybrid",
    "Spot simplifier policy: basics | full | hybrid",
    env="KR_SIMP_OPTS")

SIMP_FULL_LIMIT = OptionSpec(
    "kr.simp.full_limit", 2000,
    "hybrid policy: use full rules below this unfolded-tree size, basics above",
    env="KR_SIMP_FULL_LIMIT")

SIMP_OWN_LIMIT = OptionSpec(
    "kr.simp.own_limit", 2000,
    "cap on the own simplify pipeline (skip above this node size)",
    env="KR_SIMP_OWN_LIMIT")

# --- the package's declared option sets ---
# The Bucket-1 sub-list the portfolio builder threads now (read via options.get).
KR_DISPATCH_OPTIONS = [DISPATCH_ACC, DISPATCH_WEAK, DISPATCH_BUCHI, DISPATCH_COBUCHI]

# The full contract (all buckets), for the root builder's env-bridge aggregation.
KR_OPTIONS = KR_DISPATCH_OPTIONS + [
    FOLD_FIN_REACH, FUSE_LETTERS, SIMP_OWN, SIMP_OWN_FOLD, SIMP_OWN_FACTOR,
    TRACE, REACH_GUARD, MAX_LEVELS, FLATTEN_TREE_LIMIT,
    SIMP_NODE, SIMP_TREE_LIMIT, SIMP_OPTS, SIMP_FULL_LIMIT, SIMP_OWN_LIMIT,
]

__all__ = [
    "DISPATCH_ACC", "DISPATCH_WEAK", "DISPATCH_BUCHI", "DISPATCH_COBUCHI",
    "FOLD_FIN_REACH", "FUSE_LETTERS", "SIMP_OWN", "SIMP_OWN_FOLD", "SIMP_OWN_FACTOR",
    "TRACE", "REACH_GUARD", "MAX_LEVELS", "FLATTEN_TREE_LIMIT",
    "SIMP_NODE", "SIMP_TREE_LIMIT", "SIMP_OPTS", "SIMP_FULL_LIMIT", "SIMP_OWN_LIMIT",
    "KR_DISPATCH_OPTIONS", "KR_OPTIONS",
]
