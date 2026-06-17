"""
kr/gap/parse.py

Focused service: parsing the structured textual output emitted by the
self-contained GAP scripts generated for SgpDec holonomy decomposition.

This was extracted from aut2ltl.bls.gap.bridge so that the bridge module
can stay small and focused on "orchestration + script generation + execution",
while parsing (a distinct, testable concern that produces Cascade objects)
lives in its own small file.

The output format is deliberately simple (KEY: value and STATE ... CONFIG ... lines)
so the parser can be robust against small changes in SgpDec pretty-printers.
"""

from __future__ import annotations
import re
from typing import List, Optional

from ..cascade import Cascade, LevelInfo


# ---------------------------------------------------------------------------
# Regexes for the structured GAP output we asked the script to emit.
# These are the only thing the Python side relies on; everything else in
# the GAP script is just for human debugging.
# ---------------------------------------------------------------------------
_STATE_LINE = re.compile(r"^STATE\s+(\d+)\s+CONFIG\s+\[([^\]]*)\]", re.MULTILINE)
_LEVEL_LINE = re.compile(r"^LEVEL\s+(\d+)\s+SIZE\s+(\d+)\s+KIND\s+(\S+)(?:\s+STRUCT\s+(\S+))?", re.MULTILINE)
_NUM_LEVELS = re.compile(r"^NUM_LEVELS:\s*(\d+)", re.MULTILINE)
_NUM_STATES = re.compile(r"^NUM_STATES:\s*(\d+)", re.MULTILINE)
_SEMI_SIZE = re.compile(r"^SEMI_GROUP_SIZE:\s*(\d+)", re.MULTILINE)
_APERIODIC = re.compile(r"^APERIODIC:\s*(true|false)", re.MULTILINE)
_TRANS_LINE = re.compile(r"^TRANS\s+\[([^\]]*)\]\s+GEN\s+(\d+)\s+TO\s+\[([^\]]*)\]", re.MULTILINE)
_PI_LINE = re.compile(r"^PI\s+\[([^\]]*)\]\s+POINT\s+(\d+)", re.MULTILINE)


def _coords(s: str) -> tuple:
    """Parse a GAP coordinate list body and REVERSE it.

    SgpDec emits coords top-first (position i depends on positions 1..i-1,
    i.e. on the UPPER prefix). The kr operators peel index 0 first and treat
    the SUFFIX as the self-contained lower cascade (the paper peels the
    DEEPEST level first). Reversing at the parse boundary makes the two
    conventions coincide: python index 0 = deepest level, suffix = the
    upper sub-cascade it depends on.
    """
    s = s.strip()
    if not s:
        return ()
    return tuple(int(x.strip()) for x in reversed(s.split(",")))


def parse_cascade_output(raw: str, generators: Optional[List[List[int]]] = None) -> Cascade:
    """Parse the CASCADE_START ... CASCADE_END block (and surrounding keys).

    This is the only function most callers need. It is tolerant of extra
    output from GAP and still returns the best Cascade it can.
    """
    # We are tolerant: we look for the markers but also accept data outside them.
    m_nl = _NUM_LEVELS.search(raw)
    num_levels = int(m_nl.group(1)) if m_nl else 0

    m_ns = _NUM_STATES.search(raw)
    num_states = int(m_ns.group(1)) if m_ns else 0

    levels: List[LevelInfo] = []
    for m in _LEVEL_LINE.finditer(raw):
        idx = int(m.group(1))
        sz = int(m.group(2))
        kind = m.group(3)
        struct = m.group(4)
        levels.append(LevelInfo(index=idx, size=sz, kind=kind, structure=struct))

    if not num_levels and levels:
        num_levels = len(levels)

    # Levels are reversed like the coords (deepest-first on the python side).
    levels = [LevelInfo(index=i, size=lv.size, kind=lv.kind, structure=lv.structure)
              for i, lv in enumerate(reversed(levels))]

    state_to_config: dict[int, tuple[int, ...]] = {}
    for m in _STATE_LINE.finditer(raw):
        state_to_config[int(m.group(1))] = _coords(m.group(2))

    # True cascade transitions (BFS closure of the state lifts) and the cover
    # map pi: closure config -> original state. pi is many-to-one (holonomy
    # coordinatization is a COVER, not an isomorphism): several configs may
    # represent the same state, and the dynamics on configs is NOT the
    # h-conjugated dynamics of D — it must come from these TRANS lines.
    transitions: dict[tuple[int, ...], dict[int, tuple[int, ...]]] = {}
    for m in _TRANS_LINE.finditer(raw):
        src = _coords(m.group(1))
        transitions.setdefault(src, {})[int(m.group(2))] = _coords(m.group(3))

    config_to_state: dict[tuple[int, ...], int] = {
        _coords(m.group(1)): int(m.group(2)) for m in _PI_LINE.finditer(raw)
    }
    if not config_to_state:
        # Legacy output (no PI lines): fall back to inverting the lift.
        config_to_state = {cfg: st for st, cfg in state_to_config.items()}

    meta = {}
    m_ss = _SEMI_SIZE.search(raw)
    if m_ss:
        meta["semigroup_size"] = int(m_ss.group(1))

    # LTL-definability oracle (GAP IsAperiodicSemigroup). None if the script
    # predates the APERIODIC line (legacy output).
    m_ap = _APERIODIC.search(raw)
    aperiodic = (m_ap.group(1) == "true") if m_ap else None

    if "CASCADE_START" not in raw or "CASCADE_END" not in raw:
        # Still try to return what we got; the caller can decide if it's usable.
        meta["warning"] = "CASCADE markers not found — partial parse"

    return Cascade(
        num_levels=num_levels or len(levels),
        levels=levels,
        num_states=num_states or len(state_to_config),
        state_to_config=state_to_config,
        config_to_state=config_to_state,
        generator_images=generators or [],
        raw_output=raw,
        metadata=meta,
        transitions=transitions,
        aperiodic=aperiodic,
    )
