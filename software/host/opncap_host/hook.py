# SPDX-License-Identifier: Apache-2.0
"""micro-hook: forwards an agent hook payload from stdin to the daemon.

It never fails. It prints only a PermissionRequest decision (with --wait, after a key press on
the pad); a missing daemon or a timeout prints nothing, so the agent asks in the terminal as usual.
"""
import json
import sys

from .daemon import send_to_daemon


def decision_output(decision: str) -> str:
    """Claude Code PermissionRequest answer. The deny shape is not verified yet [prüfen]."""
    body = {"behavior": decision}
    if decision == "deny":
        body["message"] = "Denied with the opncap pad"
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": body}})


def main(argv=None, stdin=None, stdout=None, send=send_to_daemon) -> int:
    argv = sys.argv[1:] if argv is None else argv
    wait = None
    if "--wait" in argv:
        i = argv.index("--wait")
        try:
            wait = float(argv[i + 1])
        except (IndexError, ValueError):
            print("usage: micro-hook claude-code [--wait SECONDS]", file=sys.stderr)
            return 2
        del argv[i:i + 2]
    if len(argv) != 1:
        print("usage: micro-hook claude-code [--wait SECONDS]   (hook JSON on stdin)", file=sys.stderr)
        return 2
    try:
        payload = json.load(stdin or sys.stdin)
    except ValueError:
        return 0
    if wait and payload.get("hook_event_name") == "PermissionRequest":
        decision = send(argv[0], payload, wait=wait)
        if decision in ("allow", "deny"):
            print(decision_output(decision), file=stdout or sys.stdout)
        return 0  # no decision: Claude Code shows its normal prompt
    send(argv[0], payload)
    return 0


def run() -> None:
    sys.exit(main())
