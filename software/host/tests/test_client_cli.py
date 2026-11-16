# SPDX-License-Identifier: Apache-2.0
import io
import unittest
from contextlib import redirect_stderr

from opncap_host import cli, protocol as p
from opncap_host.client import Client, Rejected, Timeout
from opncap_host.transport import DeviceNotFound, TransportError


class FakePad:
    """Scripted transport: answers commands the way the firmware does."""

    def __init__(self, ack_status=0, silent=False, noise=()):
        self.ack_status = ack_status
        self.silent = silent
        self.noise = list(noise)
        self.written = []
        self.queue = []
        self.closed = False

    def write(self, frame):
        self.written.append(frame)
        name, seq, fields = p.parse(frame)
        self.queue.extend(self.noise)  # events that arrive before the reply
        if self.silent:
            return
        if name == "get_version":
            self.queue.append(p.build("version_info", seq, protocol=1, major=0, minor=1, patch=0))
        else:
            self.queue.append(p.build("ack", seq, msg=p.MESSAGES[name][0], status=self.ack_status))

    def read(self, timeout_ms):
        return self.queue.pop(0) if self.queue else None

    def close(self):
        self.closed = True


def run_cli(argv, pad=None, error=None):
    def opener(path):
        if error:
            raise error
        return pad

    err = io.StringIO()
    with redirect_stderr(err):
        code = cli.main(argv, open_transport=opener)
    return code, err.getvalue()


class ClientTest(unittest.TestCase):
    def test_set_state_sends_state_value(self):
        pad = FakePad()
        Client(pad).set_state("done")
        name, _, fields = p.parse(pad.written[0])
        self.assertEqual((name, fields), ("set_state", {"state": p.STATE["done"]}))

    def test_get_version(self):
        self.assertEqual(Client(FakePad()).get_version()["minor"], 1)

    def test_events_before_the_reply_are_skipped(self):
        noise = [p.build("key_event", 200, key=3, pressed=1), p.build("encoder_event", 201, delta=1)]
        Client(FakePad(noise=noise)).set_state("idle")

    def test_rejected(self):
        with self.assertRaises(Rejected):
            Client(FakePad(ack_status=1)).set_state("idle")

    def test_timeout(self):
        with self.assertRaises(Timeout):
            Client(FakePad(silent=True)).set_state("idle", timeout=0.05)

    def test_sequence_increments(self):
        pad = FakePad()
        c = Client(pad)
        c.set_state("idle")
        c.set_state("done")
        self.assertEqual([p.parse(f)[1] for f in pad.written], [1, 2])


class CliTest(unittest.TestCase):
    def test_ok(self):
        pad = FakePad()
        code, _ = run_cli(["thinking"], pad)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertTrue(pad.closed)

    def test_no_device(self):
        code, err = run_cli(["idle"], error=DeviceNotFound("no opncap pad found"))
        self.assertEqual(code, cli.EXIT_NO_DEVICE)
        self.assertIn("no opncap pad", err)

    def test_missing_hid_package(self):
        code, _ = run_cli(["idle"], error=TransportError("the 'hid' package is not installed"))
        self.assertEqual(code, cli.EXIT_ERROR)

    def test_timeout(self):
        code, _ = run_cli(["idle", "--timeout", "0.05"], FakePad(silent=True))
        self.assertEqual(code, cli.EXIT_TIMEOUT)

    def test_rejected(self):
        code, _ = run_cli(["error"], FakePad(ack_status=1))
        self.assertEqual(code, cli.EXIT_REJECTED)

    def test_bad_state_is_a_usage_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            cli.main(["bogus"], open_transport=lambda path: FakePad())
        self.assertEqual(cm.exception.code, cli.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
