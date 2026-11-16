<!-- SPDX-License-Identifier: GPL-2.0-or-later -->
# Firmware

QMK external userspace for the WeAct BlackPill F411 (GPL-2.0-or-later). Keyboard: `qmk_userspace/keyboards/opncap/opncap_v0_3/`. The protocol header `opncap_protocol.h` in that folder is generated from `software/protocol/protocol.yaml`; do not edit it.

Status: written against the QMK sources and docs, **not compiled and not tested on hardware**. The `firmware` job in `.github/workflows/ci.yml` is the first build; expect fixes after its first run.

Done: 4x4 matrix (14 keys, encoder push, joystick push), six layers (K11 cycles them), encoder events, Hall joystick with start calibration and min/max tracking (8 directions, 7 radial slots), raw HID with `get_version` and acknowledgements.
Not yet: RGB (feature 5), display (feature 12), microphone, joystick/encoder per-layer configuration, USB VID/PID (placeholder `0xFEED:0x0003`).

Host discovery: raw HID usage page `0xFF60`, usage `0x61` (QMK defaults).

Local build (needs the ARM toolchain and a QMK checkout):

```sh
qmk config user.overlay_dir="$(realpath software/firmware/qmk_userspace)"
qmk compile -kb opncap/opncap_v0_3 -km default
```
