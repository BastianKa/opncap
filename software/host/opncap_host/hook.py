# SPDX-License-Identifier: Apache-2.0
"""micro-hook: forwards an agent hook payload from stdin to the daemon.

It never fails and never prints: a missing daemon must not disturb the agent.
"""
import json
import sys

from .daemon import send_to_daemon


def main(argv=None, stdin=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: micro-hook claude-code   (hook JSON on stdin)", file=sys.stderr)
        return 2
    try:
        payload = json.load(stdin or sys.stdin)
    except ValueError:
        return 0
    send_to_daemon(argv[0], payload)
    return 0


def run() -> None:
    sys.exit(main())
