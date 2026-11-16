# SPDX-License-Identifier: Apache-2.0
"""micro-state: set the pad's overall state from a shell, a hook or a script."""
import argparse
import sys

from . import protocol as p
from .client import Client, Rejected, Timeout
from .transport import DeviceNotFound, HidTransport, TransportError

EXIT_OK = 0
EXIT_USAGE = 2      # argparse default
EXIT_NO_DEVICE = 3
EXIT_TIMEOUT = 4
EXIT_REJECTED = 5
EXIT_ERROR = 6


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="micro-state", description="Set the opncap pad state.")
    ap.add_argument("state", choices=[s for s in p.STATE if s != "off"] + ["off"])
    ap.add_argument("--device", help="HID device path (default: find the pad automatically)")
    ap.add_argument("--timeout", type=float, default=1.0, help="seconds to wait for the pad (default 1.0)")
    return ap


def main(argv=None, open_transport=HidTransport.open) -> int:
    args = build_parser().parse_args(argv)
    try:
        transport = open_transport(args.device)
    except DeviceNotFound as exc:
        print(f"micro-state: {exc}", file=sys.stderr)
        return EXIT_NO_DEVICE
    except TransportError as exc:
        print(f"micro-state: {exc}", file=sys.stderr)
        return EXIT_ERROR
    try:
        Client(transport).set_state(args.state, args.timeout)
    except Timeout as exc:
        print(f"micro-state: {exc}", file=sys.stderr)
        return EXIT_TIMEOUT
    except Rejected as exc:
        print(f"micro-state: {exc}", file=sys.stderr)
        return EXIT_REJECTED
    except TransportError as exc:
        print(f"micro-state: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        transport.close()
    return EXIT_OK


def run() -> None:
    sys.exit(main())
