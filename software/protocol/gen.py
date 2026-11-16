#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the C header and the Python module from protocol.yaml.

Usage: gen.py            write the generated files
       gen.py --check    fail if the generated files are out of date
"""
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SRC = HERE / "protocol.yaml"
OUT_C = HERE.parent / "firmware" / "qmk_userspace" / "keyboards" / "opncap" / "opncap_v0_3" / "opncap_protocol.h"
OUT_PY = HERE.parent / "host" / "opncap_host" / "protocol.py"

SIZES = {"u8": 1, "i8": 1, "u16": 2, "i16": 2}
CTYPES = {"u8": "uint8_t", "i8": "int8_t", "u16": "uint16_t", "i16": "int16_t"}
STRUCT = {"u8": "B", "i8": "b", "u16": "H", "i16": "h"}
HEADER = "Generated from software/protocol/protocol.yaml by software/protocol/gen.py. Do not edit."


def load():
    spec = yaml.safe_load(SRC.read_text())
    p = spec["protocol"]
    ids = set()
    for name, m in spec["messages"].items():
        assert m["id"] not in ids, f"duplicate message id {m['id']}"
        ids.add(m["id"])
        m["size"] = sum(SIZES[f["type"]] for f in m["fields"])
        assert m["size"] <= p["max_payload"], f"{name}: payload too large"
        assert p["frame_size"] == 6 + p["max_payload"] + 2
    return spec


def gen_c(spec):
    p = spec["protocol"]
    o = [f"/* SPDX-License-Identifier: Apache-2.0 */", f"/* {HEADER} */",
         "#ifndef OPNCAP_PROTOCOL_H", "#define OPNCAP_PROTOCOL_H", "",
         "#include <stddef.h>", "#include <stdint.h>", "#include <string.h>", ""]
    o += [f"#define OPNCAP_PROTOCOL_VERSION {p['version']}",
          f"#define OPNCAP_FRAME_SIZE {p['frame_size']}",
          f"#define OPNCAP_MAX_PAYLOAD {p['max_payload']}",
          f"#define OPNCAP_MAGIC0 0x{p['magic'][0]:02X}",
          f"#define OPNCAP_MAGIC1 0x{p['magic'][1]:02X}", ""]
    for ename, vals in spec["enums"].items():
        for k, v in vals.items():
            o.append(f"#define OPNCAP_{ename.upper()}_{k.upper()} {v}")
        o.append("")
    for name, m in spec["messages"].items():
        o.append(f"#define OPNCAP_MSG_{name.upper()} 0x{m['id']:02X}")
        o.append(f"#define OPNCAP_MSG_{name.upper()}_SIZE {m['size']}")
        off = 0
        for f in m["fields"]:
            o.append(f"#define OPNCAP_MSG_{name.upper()}_{f['name'].upper()}_OFFSET {off}")
            off += SIZES[f["type"]]
    o += ["", "enum {", "    OPNCAP_OK = 0,", "    OPNCAP_ERR_MAGIC = -1,", "    OPNCAP_ERR_VERSION = -2,",
          "    OPNCAP_ERR_LENGTH = -3,", "    OPNCAP_ERR_PADDING = -4,", "    OPNCAP_ERR_CRC = -5,", "};", "",
          "typedef struct {", "    uint8_t version;", "    uint8_t msg;", "    uint8_t seq;", "    uint8_t len;",
          "    uint8_t payload[OPNCAP_MAX_PAYLOAD];", "} opncap_frame_t;", "",
          "/* CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no xorout. Check value of \"123456789\" is 0x29B1. */",
          "static inline uint16_t opncap_crc16(const uint8_t *data, size_t len) {",
          "    uint16_t crc = 0xFFFF;",
          "    for (size_t i = 0; i < len; i++) {",
          "        crc ^= (uint16_t)data[i] << 8;",
          "        for (int b = 0; b < 8; b++) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);",
          "    }", "    return crc;", "}", "",
          "/* Returns 0 on success, -1 if the payload is too long. */",
          "static inline int opncap_frame_encode(const opncap_frame_t *f, uint8_t out[OPNCAP_FRAME_SIZE]) {",
          "    if (f->len > OPNCAP_MAX_PAYLOAD) return -1;",
          "    memset(out, 0, OPNCAP_FRAME_SIZE);",
          "    out[0] = OPNCAP_MAGIC0; out[1] = OPNCAP_MAGIC1; out[2] = f->version; out[3] = f->msg;",
          "    out[4] = f->seq; out[5] = f->len;",
          "    memcpy(&out[6], f->payload, f->len);",
          "    uint16_t crc = opncap_crc16(out, OPNCAP_FRAME_SIZE - 2);",
          "    out[OPNCAP_FRAME_SIZE - 2] = (uint8_t)(crc & 0xFF); out[OPNCAP_FRAME_SIZE - 1] = (uint8_t)(crc >> 8);",
          "    return 0;", "}", "",
          "/* Returns OPNCAP_OK or a negative OPNCAP_ERR_* code. */",
          "static inline int opncap_frame_decode(const uint8_t in[OPNCAP_FRAME_SIZE], opncap_frame_t *f) {",
          "    if (in[0] != OPNCAP_MAGIC0 || in[1] != OPNCAP_MAGIC1) return OPNCAP_ERR_MAGIC;",
          "    uint16_t crc = (uint16_t)(in[OPNCAP_FRAME_SIZE - 2] | (in[OPNCAP_FRAME_SIZE - 1] << 8));",
          "    if (crc != opncap_crc16(in, OPNCAP_FRAME_SIZE - 2)) return OPNCAP_ERR_CRC;",
          "    if (in[2] != OPNCAP_PROTOCOL_VERSION) return OPNCAP_ERR_VERSION;",
          "    if (in[5] > OPNCAP_MAX_PAYLOAD) return OPNCAP_ERR_LENGTH;",
          "    for (size_t i = 6 + in[5]; i < OPNCAP_FRAME_SIZE - 2; i++) if (in[i] != 0) return OPNCAP_ERR_PADDING;",
          "    f->version = in[2]; f->msg = in[3]; f->seq = in[4]; f->len = in[5];",
          "    memset(f->payload, 0, OPNCAP_MAX_PAYLOAD);",
          "    memcpy(f->payload, &in[6], f->len);",
          "    return OPNCAP_OK;", "}", "", "#endif /* OPNCAP_PROTOCOL_H */", ""]
    return "\n".join(o)


def gen_py(spec):
    p = spec["protocol"]
    o = ["# SPDX-License-Identifier: Apache-2.0", f"# {HEADER}", '"""opncap raw HID protocol bindings."""', "",
         "import struct", "from dataclasses import dataclass", "",
         f"PROTOCOL_VERSION = {p['version']}", f"FRAME_SIZE = {p['frame_size']}",
         f"MAX_PAYLOAD = {p['max_payload']}", f"MAGIC = bytes({p['magic']!r})", ""]
    for ename, vals in spec["enums"].items():
        o.append(f"{ename.upper()} = {vals!r}")
    o.append("")
    o.append("# message name -> (id, struct format, field names)")
    o.append("MESSAGES = {")
    for name, m in spec["messages"].items():
        fmt = "<" + "".join(STRUCT[f["type"]] for f in m["fields"])
        names = tuple(f["name"] for f in m["fields"])
        o.append(f"    {name!r}: (0x{m['id']:02X}, {fmt!r}, {names!r}),")
    o += ["}", "MESSAGE_IDS = {v[0]: k for k, v in MESSAGES.items()}", "",
          "",
          "class ProtocolError(ValueError):", '    """Raised for a frame that cannot be decoded."""', "", "",
          "def crc16(data: bytes) -> int:",
          '    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no xorout)."""',
          "    crc = 0xFFFF", "    for byte in data:", "        crc ^= byte << 8",
          "        for _ in range(8):",
          "            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF",
          "    return crc", "", "",
          "@dataclass", "class Frame:", "    msg: int", "    seq: int", "    payload: bytes = b''",
          "    version: int = PROTOCOL_VERSION", "", "",
          "def encode(frame: Frame) -> bytes:",
          "    if len(frame.payload) > MAX_PAYLOAD:",
          "        raise ProtocolError('payload too long')",
          "    body = (MAGIC + bytes([frame.version, frame.msg, frame.seq, len(frame.payload)])",
          "            + frame.payload.ljust(MAX_PAYLOAD, b'\\x00'))",
          "    return body + struct.pack('<H', crc16(body))", "", "",
          "def decode(data: bytes) -> Frame:",
          "    if len(data) != FRAME_SIZE:",
          "        raise ProtocolError('wrong frame size')",
          "    if data[:2] != MAGIC:",
          "        raise ProtocolError('bad magic')",
          "    if struct.unpack('<H', data[-2:])[0] != crc16(data[:-2]):",
          "        raise ProtocolError('bad crc')",
          "    version, msg, seq, length = data[2], data[3], data[4], data[5]",
          "    if version != PROTOCOL_VERSION:",
          "        raise ProtocolError('unsupported version')",
          "    if length > MAX_PAYLOAD:",
          "        raise ProtocolError('bad length')",
          "    if any(data[6 + length:FRAME_SIZE - 2]):",
          "        raise ProtocolError('nonzero padding')",
          "    return Frame(msg=msg, seq=seq, payload=bytes(data[6:6 + length]), version=version)", "", "",
          "def build(name: str, seq: int, **fields) -> bytes:",
          '    """Encode message `name` with the given field values."""',
          "    msg_id, fmt, names = MESSAGES[name]",
          "    if set(fields) != set(names):",
          "        raise ProtocolError(f'{name} needs fields {names}')",
          "    payload = struct.pack(fmt, *(fields[n] for n in names))",
          "    return encode(Frame(msg=msg_id, seq=seq, payload=payload))", "", "",
          "def parse(data: bytes):",
          '    """Decode a frame into (name, seq, fields)."""',
          "    frame = decode(data)",
          "    if frame.msg not in MESSAGE_IDS:",
          "        raise ProtocolError('unknown message')",
          "    name = MESSAGE_IDS[frame.msg]",
          "    _, fmt, names = MESSAGES[name]",
          "    if len(frame.payload) != struct.calcsize(fmt):",
          "        raise ProtocolError('payload size mismatch')",
          "    return name, frame.seq, dict(zip(names, struct.unpack(fmt, frame.payload)))", ""]
    return "\n".join(o)


def main():
    spec = load()
    outputs = {OUT_C: gen_c(spec), OUT_PY: gen_py(spec)}
    if "--check" in sys.argv:
        stale = [str(p) for p, t in outputs.items() if not p.exists() or p.read_text() != t]
        if stale:
            sys.exit("generated files out of date, run gen.py: " + ", ".join(stale))
        print("generated files are up to date")
        return
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print("wrote", path.relative_to(HERE.parent))


if __name__ == "__main__":
    main()
