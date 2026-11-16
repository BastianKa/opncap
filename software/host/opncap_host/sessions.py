# SPDX-License-Identifier: Apache-2.0
"""Agent sessions and their LED slots."""
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

SLOTS = 6
# Overall state shown on the status light: the most urgent session wins.
PRIORITY = ["off", "idle", "done", "thinking", "input", "error"]
STALE_AFTER = 120.0  # seconds a session may stay "thinking" without any new event


@dataclass
class Session:
    session_id: str
    cwd: str
    slot: int
    state: str = "idle"
    updated: float = 0.0


class SessionRegistry:
    """Maps agent sessions to the six agent keys."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, stale_after: float = STALE_AFTER):
        self._clock = clock
        self._stale_after = stale_after
        self._sessions: Dict[str, Session] = {}

    def _free_slot(self) -> int:
        used = {s.slot for s in self._sessions.values()}
        for slot in range(SLOTS):
            if slot not in used:
                return slot
        # All slots taken: reuse the one of the least urgent, least recently updated session.
        victim = min(self._sessions.values(), key=lambda s: (PRIORITY.index(s.state), s.updated))
        del self._sessions[victim.session_id]
        return victim.slot

    def update(self, session_id: str, cwd: str, state: str) -> List[Tuple[int, str]]:
        """Record a state; returns the (slot, state) changes to send to the pad."""
        changes: List[Tuple[int, str]] = []
        s = self._sessions.get(session_id)
        if s is None:
            slot = self._free_slot()
            s = self._sessions[session_id] = Session(session_id, cwd, slot, state, self._clock())
            return [(slot, state)]
        s.cwd = cwd or s.cwd
        s.updated = self._clock()
        if s.state != state:
            s.state = state
            changes.append((s.slot, state))
        return changes

    def end(self, session_id: str) -> List[Tuple[int, str]]:
        s = self._sessions.pop(session_id, None)
        return [(s.slot, "off")] if s else []

    def expire(self) -> List[Tuple[int, str]]:
        """Sessions stuck in 'thinking' (for example after an interrupt, when no Stop arrives) fall back to idle."""
        now, changes = self._clock(), []
        for s in self._sessions.values():
            if s.state == "thinking" and now - s.updated > self._stale_after:
                s.state = "idle"
                changes.append((s.slot, "idle"))
        return changes

    def overall(self) -> str:
        if not self._sessions:
            return "off"
        return max((s.state for s in self._sessions.values()), key=PRIORITY.index)

    def slot_states(self) -> Dict[int, str]:
        return {s.slot: s.state for s in self._sessions.values()}
