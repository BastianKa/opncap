<!-- SPDX-License-Identifier: Apache-2.0 -->
# opncap host

Python package `opncap_host`: protocol bindings (generated, `protocol.py`), transport (raw HID through the `hid` package), a request/reply client and the CLI `micro-state`.

Status: tested against a fake pad only. **Not tested with a real device.** The firmware answers `set_state` with `unknown_message` until the LED feature exists, so `micro-state` currently exits with code 5 on real hardware.

```sh
pip install ./software/host        # installs the `micro-state` command and `hid`
micro-state thinking               # idle | thinking | done | input | error | off
micro-state done --timeout 2 --device /dev/hidraw3
```

Exit codes: 0 ok, 2 usage error, 3 no pad found, 4 no reply in time, 5 pad rejected the command, 6 other error (for example `hid` not installed).

Linux: copy `udev/99-opncap.rules` to `/etc/udev/rules.d/` and reload udev. macOS: the first run may need the "Input Monitoring" permission for the terminal [prüfen]. Windows is not supported in phase 1.

Not yet built: the background service that owns the device and tracks several agent sessions (comes with the agent status feature), tray icon, autostart.

Tests: `make test` in `software/` (uses a fake pad, no hardware or `hid` needed).
