# SPDX-License-Identifier: Apache-2.0
"""Host service: owns the pad, receives agent events on a local socket and drives the LEDs."""
import json
import os
import socketserver
import sys
import threading
from pathlib import Path
from typing import Callable, List, Optional

from . import protocol as p
from .adapters import claude_code
from .engine import Engine, load_bindings
from .client import Client, Rejected, Timeout
from .sessions import SessionRegistry
from .transport import DeviceNotFound, HidTransport, TransportError

MAX_MESSAGE = 64 * 1024


def default_socket_path() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or str(Path.home() / ".opncap")
    Path(base).mkdir(parents=True, exist_ok=True)
    return str(Path(base) / "opncap.sock")


class Controller:
    """Turns agent events into pad commands. No sockets here, so it is easy to test."""

    def __init__(self, open_transport: Callable[[], object] = HidTransport.open,
                 registry: Optional[SessionRegistry] = None, log=lambda msg: None,
                 engine: Optional[Engine] = None):
        self._open = open_transport
        self.registry = registry or SessionRegistry()
        self._log = log
        self._client: Optional[Client] = None
        self.debug = False  # log every incoming agent event (for live tests without a pad)
        self._lock = threading.Lock()
        self.engine = engine or Engine(self, log=log)
        self._pending: List["_Pending"] = []  # permission requests waiting for a key, oldest first
        self._pending_lock = threading.Lock()

    def _get_client(self) -> Optional[Client]:
        if self._client is not None and not self._client.alive:
            self._client = None  # reader saw the pad disappear
        if self._client is None:
            try:
                self._client = Client(self._open())
                self._client.start(self.engine.on_pad_event)
            except (DeviceNotFound, TransportError) as exc:
                self._log(f"pad not available: {exc}")
                return None
        return self._client

    def _send(self, changes) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            for slot, state in changes:
                client.request("set_agent_state", slot=slot, state=p.STATE[state])
            client.set_state(self.registry.overall())
        except Rejected as exc:
            self._log(f"pad rejected a command: {exc}")  # firmware without LED support yet
        except (Timeout, TransportError) as exc:
            self._log(f"pad not responding: {exc}")
            self._client = None  # reopen on the next event

    def handle(self, source: str, payload: dict) -> None:
        if source != "claude-code":
            self._log(f"unknown source {source!r}")
            return
        mapped = claude_code.map_event(payload)
        if self.debug:
            self._log(f"event {payload.get('hook_event_name')!r} session={str(payload.get('session_id'))[:8]} "
                      f"notification_type={payload.get('notification_type')!r} -> {mapped[2] if mapped else 'ignored'}")
        if mapped is None:
            return
        session_id, cwd, state = mapped
        with self._lock:
            changes = (self.registry.end(session_id) if state == claude_code.END
                       else self.registry.update(session_id, cwd, state))
            if changes:
                self._send(changes)

    # --- permission requests (Claude Code PermissionRequest hook) ----------------
    def wait_for_decision(self, payload: dict, timeout: float) -> Optional[str]:
        """Show the request as 'input' and wait for the approve or deny key.

        Returns "allow", "deny" or None (timeout: the normal prompt in the terminal decides).
        """
        pending = _Pending(payload.get("session_id", ""))
        with self._pending_lock:
            self._pending.append(pending)
        try:
            self.handle("claude-code", payload)  # orange LED
            if not pending.event.wait(timeout):
                return None
            return pending.decision
        finally:
            with self._pending_lock:
                if pending in self._pending:
                    self._pending.remove(pending)

    def resolve_permission(self, decision: str) -> bool:
        """Answer the most recent waiting request. False if none is waiting."""
        with self._pending_lock:
            if not self._pending:
                return False
            pending = self._pending.pop()
        pending.decision = decision
        pending.event.set()
        # Back to "thinking": the tool runs (allow) or Claude reacts (deny).
        self.handle("claude-code", {"hook_event_name": "PreToolUse", "session_id": pending.session_id})
        return True

    def tick(self) -> None:
        with self._lock:
            changes = self.registry.expire()
            if changes:
                self._send(changes)


class _Pending:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.event = threading.Event()
        self.decision: Optional[str] = None


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(MAX_MESSAGE)
        try:
            msg = json.loads(line)
            wait = msg.get("wait")
            if wait and msg["payload"].get("hook_event_name") == "PermissionRequest":
                decision = self.server.controller.wait_for_decision(msg["payload"], float(wait))
                self.wfile.write(json.dumps({"decision": decision}).encode() + b"\n")
            else:
                self.server.controller.handle(msg["source"], msg["payload"])
        except (ValueError, KeyError, TypeError) as exc:
            self.server.controller._log(f"bad message: {exc}")


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, path: str, controller: Controller):
        if os.path.exists(path):
            os.unlink(path)  # stale socket from a previous run
        super().__init__(path, _Handler)
        os.chmod(path, 0o600)
        self.controller = controller


def serve(path: Optional[str] = None, controller: Optional[Controller] = None, debug: bool = False) -> None:
    path = path or default_socket_path()
    if controller is None:
        log = lambda m: print(f"opncap-daemon: {m}", file=sys.stderr)  # noqa: E731
        bindings = load_bindings(Path.home() / ".config" / "opncap" / "bindings.json")
        controller = Controller(log=log, engine=None)
        controller.engine.bindings = bindings
    controller.debug = debug
    server = Server(path, controller)
    server.timeout = 1.0
    print(f"opncap-daemon: listening on {path}", file=sys.stderr)
    try:
        while True:
            server.handle_request()
            controller.tick()
    finally:
        server.server_close()
        os.unlink(path)


def run() -> None:
    try:
        serve(debug="--debug" in sys.argv[1:])
    except KeyboardInterrupt:
        pass


def send_to_daemon(source: str, payload: dict, path: Optional[str] = None, timeout: float = 0.5,
                   wait: Optional[float] = None):
    """Send an event. Returns True/False for plain events, or the daemon's decision
    ("allow", "deny" or None) when `wait` is given."""
    import socket
    path = path or default_socket_path()
    msg = {"source": source, "payload": payload}
    if wait:
        msg["wait"] = wait
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(wait + 2 if wait else timeout)
            s.connect(path)
            s.sendall(json.dumps(msg).encode() + b"\n")
            if not wait:
                return True
            return json.loads(s.makefile().readline() or "{}").get("decision")
    except (OSError, ValueError):
        return None if wait else False
