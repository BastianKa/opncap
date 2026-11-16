# SPDX-License-Identifier: Apache-2.0
"""Request/reply client for the pad, with an optional reader thread for pad events."""
import queue
import threading
import time
from typing import Callable, Optional

from . import protocol as p
from .transport import Transport, TransportError


class Timeout(Exception):
    pass


class Rejected(Exception):
    def __init__(self, status: int):
        super().__init__(f"device rejected the command (status {status})")
        self.status = status


class Client:
    """Without start(), request() reads the transport itself and skips events (CLI use).

    After start(on_event), a reader thread owns the transport: replies go to request(),
    everything else (keys, encoder, joystick, layer) goes to on_event(name, fields).
    """

    def __init__(self, transport: Transport):
        self._t = transport
        self._seq = 0
        self._replies: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.alive = True

    # --- reader thread ---------------------------------------------------------
    def start(self, on_event: Callable[[str, dict], None]) -> None:
        self._thread = threading.Thread(target=self._reader, args=(on_event,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _reader(self, on_event) -> None:
        while not self._stop.is_set():
            try:
                raw = self._t.read(100)
            except (TransportError, OSError):
                self.alive = False
                return
            if raw is None:
                self._stop.wait(0.001)
                continue
            try:
                name, seq, fields = p.parse(raw)
            except p.ProtocolError:
                continue
            if name in ("ack", "version_info"):
                self._replies.put((name, seq, fields))
            else:
                try:
                    on_event(name, fields)
                except Exception:  # an action must never kill the reader
                    pass

    # --- requests --------------------------------------------------------------
    def _next_reply(self, remaining: float):
        if self._thread is not None:
            try:
                return self._replies.get(timeout=max(remaining, 0.001))
            except queue.Empty:
                return None
        raw = self._t.read(max(1, int(remaining * 1000)))
        if raw is None:
            return None
        try:
            name, seq, fields = p.parse(raw)
        except p.ProtocolError:
            return None
        return (name, seq, fields) if name in ("ack", "version_info") else None

    def request(self, name: str, timeout: float = 1.0, **fields):
        """Send a command and wait for its reply (ack or version_info with the same seq).

        Returns (reply_name, reply_fields). Raises Timeout or Rejected.
        """
        seq = self._seq = (self._seq + 1) & 0xFF
        msg_id = p.MESSAGES[name][0]
        self._t.write(p.build(name, seq, **fields))
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Timeout(f"no reply to {name} within {timeout} s")
            reply = self._next_reply(remaining)
            if reply is None:
                continue
            rname, rseq, rfields = reply
            if rseq != seq:
                continue
            if rname == "ack" and rfields["msg"] == msg_id:
                if rfields["status"] != p.ACK_STATUS["ok"]:
                    raise Rejected(rfields["status"])
                return rname, rfields
            if rname == "version_info":
                return rname, rfields

    def get_version(self, timeout: float = 1.0) -> dict:
        return self.request("get_version", timeout)[1]

    def set_state(self, state: str, timeout: float = 1.0) -> None:
        self.request("set_state", timeout, state=p.STATE[state])
