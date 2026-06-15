"""
aut2ltl/proc.py — keep our external children from outliving us.

The policy: NO RUNAWAYS. When we spawn a heavy external child (GAP, which can
balloon to GBs) we never want it surviving on its own once we're going down — if
we die or get interrupted, the whole family goes with us, one clean group kill.
A leaked GAP ate someone's machine; this file is the leash.

How: every heavy child is launched in its own process group (one
`start_new_session=True` flag — its pgid then equals its pid) and registered
here. That buys two kills:

  * timeout — a child that won't finish is killed by group (`kill_child_group`).
    This needs no signal setup, so it also covers batch/survey subprocesses; and
  * interrupt — Ctrl-C / SIGTERM / SIGHUP is caught (handlers installed once by
    `setup_signals()`, only from the CLI entry point) and every registered child
    group is killed before we exit.

We do NOT re-group our own process: the terminal sends Ctrl-C to the foreground
group, and re-grouping would cut us off from it. We never kill our own group
either — children sit in their own groups, so we kill those and re-raise the
signal on ourselves to exit normally. The kr core stays out of all this; it just
registers / unregisters / kills through the three helpers below.
"""
from __future__ import annotations

import os
import signal
from types import FrameType
from typing import Optional, Set

# Process groups of live external children (GAP). pgid == child pid, because
# every child is spawned with start_new_session=True.
_child_pgids: Set[int] = set()

# Interrupts we forward. SIGKILL/SIGSTOP are uncatchable by design and omitted.
_FORWARD_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def setup_signals() -> None:
    """Install interrupt forwarding (call once, from the CLI entry point)."""
    for sig in _FORWARD_SIGNALS:
        signal.signal(sig, _handle)


def register_child(pgid: int) -> None:
    """Record a live child's process group so interrupts reach it."""
    _child_pgids.add(pgid)


def unregister_child(pgid: int) -> None:
    """Forget a child whose group is already gone (reaped/killed)."""
    _child_pgids.discard(pgid)


def kill_child_group(pgid: int) -> None:
    """SIGKILL a child's whole process group (the timeout path)."""
    _killpg(pgid, signal.SIGKILL)
    _child_pgids.discard(pgid)


def _killpg(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _handle(signum: int, frame: Optional[FrameType]) -> None:
    # Free the RAM fast — GAP may ignore a polite signal, so go straight to KILL.
    for pgid in list(_child_pgids):
        _killpg(pgid, signal.SIGKILL)
        _child_pgids.discard(pgid)
    # Restore default disposition and re-raise so we exit conventionally.
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)
