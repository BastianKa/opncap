# SPDX-License-Identifier: Apache-2.0
# Generated from software/protocol/protocol.yaml by software/protocol/gen.py. Do not edit.
"""opncap raw HID protocol bindings."""

import struct
from dataclasses import dataclass

PROTOCOL_VERSION = 1
FRAME_SIZE = 32
MAX_PAYLOAD = 24
MAGIC = bytes([79, 67])

STATE = {'off': 0, 'idle': 1, 'thinking': 2, 'done': 3, 'input': 4, 'error': 5}
DIRECTION = {'center': 0, 'up': 1, 'up_right': 2, 'right': 3, 'down_right': 4, 'down': 5, 'down_left': 6, 'left': 7, 'up_left': 8}
ACK_STATUS = {'ok': 0, 'unknown_message': 1, 'bad_payload': 2, 'busy': 3}

# message name -> (id, struct format, field names)
MESSAGES = {
    'get_version': (0x01, '<', ()),
    'set_led': (0x02, '<BBBB', ('index', 'r', 'g', 'b')),
    'set_state': (0x03, '<B', ('state',)),
    'set_agent_state': (0x04, '<BB', ('slot', 'state')),
    'set_display': (0x05, '<BB', ('view', 'arg')),
    'set_config': (0x06, '<BH', ('key', 'value')),
    'ack': (0x70, '<BB', ('msg', 'status')),
    'version_info': (0x71, '<BBBB', ('protocol', 'major', 'minor', 'patch')),
    'key_event': (0x80, '<BB', ('key', 'pressed')),
    'encoder_event': (0x81, '<b', ('delta',)),
    'joystick_event': (0x82, '<BB', ('direction', 'slot')),
    'layer_event': (0x83, '<B', ('layer',)),
}
MESSAGE_IDS = {v[0]: k for k, v in MESSAGES.items()}


class ProtocolError(ValueError):
    """Raised for a frame that cannot be decoded."""


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no xorout)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


@dataclass
class Frame:
    msg: int
    seq: int
    payload: bytes = b''
    version: int = PROTOCOL_VERSION


def encode(frame: Frame) -> bytes:
    if len(frame.payload) > MAX_PAYLOAD:
        raise ProtocolError('payload too long')
    body = (MAGIC + bytes([frame.version, frame.msg, frame.seq, len(frame.payload)])
            + frame.payload.ljust(MAX_PAYLOAD, b'\x00'))
    return body + struct.pack('<H', crc16(body))


def decode(data: bytes) -> Frame:
    if len(data) != FRAME_SIZE:
        raise ProtocolError('wrong frame size')
    if data[:2] != MAGIC:
        raise ProtocolError('bad magic')
    if struct.unpack('<H', data[-2:])[0] != crc16(data[:-2]):
        raise ProtocolError('bad crc')
    version, msg, seq, length = data[2], data[3], data[4], data[5]
    if version != PROTOCOL_VERSION:
        raise ProtocolError('unsupported version')
    if length > MAX_PAYLOAD:
        raise ProtocolError('bad length')
    if any(data[6 + length:FRAME_SIZE - 2]):
        raise ProtocolError('nonzero padding')
    return Frame(msg=msg, seq=seq, payload=bytes(data[6:6 + length]), version=version)


def build(name: str, seq: int, **fields) -> bytes:
    """Encode message `name` with the given field values."""
    msg_id, fmt, names = MESSAGES[name]
    if set(fields) != set(names):
        raise ProtocolError(f'{name} needs fields {names}')
    payload = struct.pack(fmt, *(fields[n] for n in names))
    return encode(Frame(msg=msg_id, seq=seq, payload=payload))


def parse(data: bytes):
    """Decode a frame into (name, seq, fields)."""
    frame = decode(data)
    if frame.msg not in MESSAGE_IDS:
        raise ProtocolError('unknown message')
    name = MESSAGE_IDS[frame.msg]
    _, fmt, names = MESSAGES[name]
    if len(frame.payload) != struct.calcsize(fmt):
        raise ProtocolError('payload size mismatch')
    return name, frame.seq, dict(zip(names, struct.unpack(fmt, frame.payload)))
