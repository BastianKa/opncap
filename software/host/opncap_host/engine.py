# SPDX-License-Identifier: Apache-2.0
"""Action engine: turns pad events into actions through key bindings."""
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

# Matrix position (row * 4 + col) to key name, see hardware/opncap_v0.3/hardware/pinout.md.
KEY_NAMES = {i: f"K{i + 1}" for i in range(12)}
KEY_NAMES.update({12: "ENC_PUSH", 13: "K13", 14: "K14", 15: "JOY_PUSH"})

# Command keys K7..K12. Only the actions that can be done today are bound.
DEFAULT_BINDINGS = {"K8": "approve", "K9": "deny"}

_HOTKEY = re.compile(r"^[A-Za-z0-9_+\-]+$")


class HotkeySender:
    """Sends a key combination to the focused application (xdotool on Linux, osascript on macOS)."""

    def __init__(self, runner: Callable = subprocess.run, platform: str = sys.platform):
        self._run = runner
        self._platform = platform

    def send(self, combo: str) -> bool:
        if not _HOTKEY.match(combo):
            return False
        if self._platform.startswith("linux"):
            self._run(["xdotool", "key", combo], check=False, timeout=2)
            return True
        if self._platform == "darwin":
            *mods, key = combo.lower().split("+")
            names = {"cmd": "command", "ctrl": "control", "alt": "option", "opt": "option", "shift": "shift"}
            if any(m not in names for m in mods):
                return False
            using = ", ".join(f"{names[m]} down" for m in mods)
            script = f'tell application "System Events" to keystroke "{key}"' + (f" using {{{using}}}" if using else "")
            self._run(["osascript", "-e", script], check=False, timeout=2)
            return True
        return False


def load_bindings(path: Optional[Path]) -> Dict[str, str]:
    """Default bindings, overridden by a JSON file {"K8": "approve", ...} if it exists."""
    bindings = dict(DEFAULT_BINDINGS)
    if path and path.exists():
        data = json.loads(path.read_text())
        bindings.update({str(k): str(v) for k, v in data.items()})
    return bindings


class Engine:
    def __init__(self, controller, bindings: Optional[Dict[str, str]] = None,
                 hotkeys: Optional[HotkeySender] = None, log=lambda msg: None):
        self._controller = controller
        self.bindings = bindings if bindings is not None else dict(DEFAULT_BINDINGS)
        self._hotkeys = hotkeys or HotkeySender()
        self._log = log

    def on_pad_event(self, name: str, fields: dict) -> None:
        if name != "key_event" or not fields.get("pressed"):
            return
        label = KEY_NAMES.get(fields["key"])
        action = self.bindings.get(label)
        if action:
            self.run(action)

    def run(self, action: str) -> bool:
        if action == "approve":
            return self._controller.resolve_permission("allow")
        if action == "deny":
            return self._controller.resolve_permission("deny")
        if action.startswith("hotkey:"):
            ok = self._hotkeys.send(action[len("hotkey:"):])
            if not ok:
                self._log(f"hotkey not sent: {action!r}")
            return ok
        self._log(f"unknown action {action!r}")
        return False
