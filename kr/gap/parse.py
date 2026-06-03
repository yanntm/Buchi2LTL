"""
kr/gap/parse.py

Focused service: parsing the structured textual output emitted by the
self-contained GAP scripts generated for SgpDec holonomy decomposition.

This was extracted from kr/gap_bridge.py so that the bridge module
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

    state_to_config: dict[int, tuple[int, ...]] = {}
    for m in _STATE_LINE.finditer(raw):
        s = int(m.group(1))
        coord_str = m.group(2).strip()
        if coord_str:
            coords = tuple(int(x.strip()) for x in coord_str.split(","))
        else:
            coords = tuple()
        state_to_config[s] = coords

    # Build reverse map (last write wins if collisions — rare)
    config_to_state: dict[tuple[int, ...], int] = {
        cfg: st for st, cfg in state_to_config.items()
    }

    meta = {}
    m_ss = _SEMI_SIZE.search(raw)
    if m_ss:
        meta["semigroup_size"] = int(m_ss.group(1))

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
    )
