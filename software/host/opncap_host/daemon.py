# SPDX-License-Identifier: Apache-2.0
"""Host service: owns the pad, receives agent events on a local socket and drives the LEDs."""
import json
import os
import socketserver
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from . import protocol as p
from .adapters import claude_code
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
                 registry: Optional[SessionRegistry] = None, log=lambda msg: None):
        self._open = open_transport
        self.registry = registry or SessionRegistry()
        self._log = log
        self._client: Optional[Client] = None
        self._lock = threading.Lock()

    def _get_client(self) -> Optional[Client]:
        if self._client is None:
            try:
                self._client = Client(self._open())
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
        if mapped is None:
            return
        session_id, cwd, state = mapped
        with self._lock:
            changes = (self.registry.end(session_id) if state == claude_code.END
                       else self.registry.update(session_id, cwd, state))
            if changes:
                self._send(changes)

    def tick(self) -> None:
        with self._lock:
            changes = self.registry.expire()
            if changes:
                self._send(changes)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(MAX_MESSAGE)
        try:
            msg = json.loads(line)
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


def serve(path: Optional[str] = None, controller: Optional[Controller] = None) -> None:
    path = path or default_socket_path()
    controller = controller or Controller(log=lambda m: print(f"opncap-daemon: {m}", file=sys.stderr))
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
        serve()
    except KeyboardInterrupt:
        pass


def send_to_daemon(source: str, payload: dict, path: Optional[str] = None, timeout: float = 0.5) -> bool:
    import socket
    path = path or default_socket_path()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(path)
            s.sendall(json.dumps({"source": source, "payload": payload}).encode() + b"\n")
        return True
    except OSError:
        return False
