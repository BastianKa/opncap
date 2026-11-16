# SPDX-License-Identifier: Apache-2.0
"""Request/reply client for the pad."""
import time

from . import protocol as p
from .transport import Transport


class Timeout(Exception):
    pass


class Rejected(Exception):
    def __init__(self, status: int):
        super().__init__(f"device rejected the command (status {status})")
        self.status = status


class Client:
    def __init__(self, transport: Transport):
        self._t = transport
        self._seq = 0

    def request(self, name: str, timeout: float = 1.0, **fields):
        """Send a command and wait for its reply (ack or version_info with the same seq).

        Events from the pad (keys, encoder, joystick, layer) that arrive in between are skipped.
        Returns (reply_name, reply_fields). Raises Timeout.
        """
        seq = self._seq = (self._seq + 1) & 0xFF
        msg_id = p.MESSAGES[name][0]
        self._t.write(p.build(name, seq, **fields))
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Timeout(f"no reply to {name} within {timeout} s")
            raw = self._t.read(max(1, int(remaining * 1000)))
            if raw is None:
                continue
            try:
                reply, rseq, rfields = p.parse(raw)
            except p.ProtocolError:
                continue  # garbage or an unknown message: ignore
            if rseq != seq:
                continue
            if reply == "ack" and rfields["msg"] == msg_id:
                if rfields["status"] != p.ACK_STATUS["ok"]:
                    raise Rejected(rfields["status"])
                return reply, rfields
            if reply == "version_info":
                return reply, rfields

    def get_version(self, timeout: float = 1.0) -> dict:
        return self.request("get_version", timeout)[1]

    def set_state(self, state: str, timeout: float = 1.0) -> None:
        self.request("set_state", timeout, state=p.STATE[state])
