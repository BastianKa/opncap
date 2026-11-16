# SPDX-License-Identifier: Apache-2.0
"""Transport layer: the raw HID device, behind a small interface so tests can fake it."""
from typing import Optional, Protocol

VID = 0xFEED  # placeholder, same as firmware keyboard.json
PID = 0x0003
USAGE_PAGE = 0xFF60  # QMK raw HID defaults
USAGE = 0x61


class DeviceNotFound(Exception):
    pass


class TransportError(Exception):
    pass


class Transport(Protocol):
    def write(self, frame: bytes) -> None: ...

    def read(self, timeout_ms: int) -> Optional[bytes]:
        """Return one 32-byte frame, or None on timeout."""

    def close(self) -> None: ...


class HidTransport:
    """Raw HID transport using the `hid` package (hidapi)."""

    def __init__(self, device):
        self._dev = device

    @staticmethod
    def open(path: Optional[str] = None) -> "HidTransport":
        try:
            import hid
        except ImportError as exc:
            raise TransportError("the 'hid' package is not installed (pip install hid)") from exc
        if path is None:
            candidates = [d for d in hid.enumerate(VID, PID)
                          if d.get("usage_page") == USAGE_PAGE and d.get("usage") == USAGE]
            if not candidates:
                raise DeviceNotFound("no opncap pad found")
            path = candidates[0]["path"]
        dev = hid.device()
        try:
            dev.open_path(path if isinstance(path, bytes) else path.encode())
        except OSError as exc:
            raise DeviceNotFound(f"cannot open {path!r}: {exc}") from exc
        return HidTransport(dev)

    def write(self, frame: bytes) -> None:
        # hidapi expects the report id (0 = none) in front of the data.
        if self._dev.write(b"\x00" + frame) < 0:
            raise TransportError("write failed")

    def read(self, timeout_ms: int) -> Optional[bytes]:
        data = self._dev.read(32, timeout_ms)
        return bytes(data) if data else None

    def close(self) -> None:
        self._dev.close()
