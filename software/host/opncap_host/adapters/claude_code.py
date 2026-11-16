# SPDX-License-Identifier: Apache-2.0
"""Maps Claude Code hook payloads to pad states.

Hook events and fields follow the Claude Code hooks documentation (checked by research,
not yet against a live session). Every hook payload carries session_id and cwd.
"""
from typing import Optional, Tuple

END = "end"  # marker: the session is over

_STATE_BY_EVENT = {
    "SessionStart": "idle",
    "UserPromptSubmit": "thinking",
    "PreToolUse": "thinking",
    "PermissionRequest": "input",
    "Stop": "done",
    "StopFailure": "error",
    "SessionEnd": END,
}
_INPUT_NOTIFICATIONS = {"permission_prompt", "idle_prompt"}


def map_event(payload: dict) -> Optional[Tuple[str, str, str]]:
    """Return (session_id, cwd, state_or_END), or None if the event is irrelevant."""
    event = payload.get("hook_event_name")
    session_id = payload.get("session_id")
    if not event or not session_id:
        return None
    if event == "Notification":
        state = "input" if payload.get("notification_type") in _INPUT_NOTIFICATIONS else None
    else:
        # PostToolUseFailure (a short red flash) is not mapped yet; the session state stays as it is.
        state = _STATE_BY_EVENT.get(event)
    if state is None:
        return None
    return session_id, payload.get("cwd", ""), state
