<!-- SPDX-License-Identifier: GPL-2.0-or-later -->
# Firmware

QMK external userspace for the WeAct BlackPill F411 (GPL-2.0-or-later). Keyboard: `qmk_userspace/keyboards/opncap/opncap_v0_3/`. The protocol header `opncap_protocol.h` in that folder is generated from `software/protocol/protocol.yaml`; do not edit it.

Status: builds and links in CI against a pinned QMK commit (the binary is uploaded as a CI artifact). **Not tested on hardware.**

Done: 4x4 matrix (14 keys, encoder push, joystick push), six layers (K11 cycles them), encoder events, Hall joystick with start calibration and min/max tracking (8 directions, 7 radial slots), raw HID with `get_version` and acknowledgements, RGB matrix on a WS2812 chain (B4, PWM+DMA, 23 LEDs) with agent status colors: `set_agent_state` drives K1 to K6, `set_state` drives the status LED (white idle, blue thinking, green done, orange input, red error, off).
Not yet: pulsing of the selected agent key, brightness/dim profiles (feature 13), display (feature 12), microphone, joystick/encoder per-layer configuration, USB VID/PID (placeholder `0xFEED:0x0003`).

Host discovery: raw HID usage page `0xFF60`, usage `0x61` (QMK defaults).

Local build (needs the ARM toolchain and a QMK checkout). CI does not use the overlay: the `qmk` CLI rejected the overlay directory there, so CI copies `keyboards/opncap` into the QMK checkout instead. The overlay route below is untested.

```sh
qmk config user.overlay_dir="$(realpath software/firmware/qmk_userspace)"
qmk compile -kb opncap/opncap_v0_3 -km default
```
