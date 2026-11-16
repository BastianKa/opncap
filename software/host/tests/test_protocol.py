# SPDX-License-Identifier: Apache-2.0
import unittest
from pathlib import Path

from opncap_host import protocol as p

VECTORS = Path(__file__).resolve().parents[2] / "protocol" / "tests" / "vectors.txt"

SAMPLES = {
    "get_version": {},
    "set_led": dict(index=3, r=255, g=0, b=128),
    "set_state": dict(state=4),
    "set_agent_state": dict(slot=5, state=2),
    "set_display": dict(view=1, arg=7),
    "set_config": dict(key=2, value=60000),
    "ack": dict(msg=2, status=0),
    "version_info": dict(protocol=1, major=0, minor=1, patch=0),
    "key_event": dict(key=15, pressed=1),
    "encoder_event": dict(delta=-3),
    "joystick_event": dict(direction=2, slot=255),
    "layer_event": dict(layer=5),
}


def vectors():
    for line in VECTORS.read_text().splitlines():
        if line and not line.startswith("#"):
            yield line.split()


class CrcTest(unittest.TestCase):
    def test_check_value(self):
        self.assertEqual(p.crc16(b"123456789"), 0x29B1)

    def test_empty(self):
        self.assertEqual(p.crc16(b""), 0xFFFF)


class RoundtripTest(unittest.TestCase):
    def test_every_message_roundtrips(self):
        self.assertEqual(set(SAMPLES), set(p.MESSAGES), "add a sample for every message")
        for name, fields in SAMPLES.items():
            with self.subTest(name):
                frame = p.build(name, 9, **fields)
                self.assertEqual(len(frame), p.FRAME_SIZE)
                self.assertEqual(p.parse(frame), (name, 9, fields))

    def test_negative_delta(self):
        self.assertEqual(p.parse(p.build("encoder_event", 0, delta=-128))[2]["delta"], -128)

    def test_wrong_fields_rejected(self):
        with self.assertRaises(p.ProtocolError):
            p.build("set_led", 0, index=1)

    def test_oversized_payload_rejected(self):
        with self.assertRaises(p.ProtocolError):
            p.encode(p.Frame(msg=1, seq=0, payload=bytes(25)))


class BadFrameTest(unittest.TestCase):
    def test_wrong_size(self):
        with self.assertRaises(p.ProtocolError):
            p.decode(bytes(31))

    def test_unknown_message(self):
        with self.assertRaises(p.ProtocolError):
            p.parse(p.encode(p.Frame(msg=0x7E, seq=0)))


class VectorTest(unittest.TestCase):
    def test_valid_vectors(self):
        for kind, name, seq, hexdata in (v for v in vectors() if v[0] == "valid"):
            with self.subTest(name):
                data = bytes.fromhex(hexdata)
                self.assertEqual(p.decode(data).seq, int(seq))
                self.assertEqual(p.encode(p.decode(data)), data)
                self.assertEqual(p.parse(data)[0], name)

    def test_invalid_vectors(self):
        for kind, error, hexdata in (v for v in vectors() if v[0] == "invalid"):
            with self.subTest(error):
                with self.assertRaisesRegex(p.ProtocolError, {"magic": "magic", "crc": "crc", "version": "version",
                                                                "length": "length", "padding": "padding"}[error]):
                    p.decode(bytes.fromhex(hexdata))


if __name__ == "__main__":
    unittest.main()
