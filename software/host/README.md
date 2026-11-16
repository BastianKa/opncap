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

## Agent status (Claude Code)

`opncap-daemon` owns the pad and listens on a Unix socket (`$XDG_RUNTIME_DIR/opncap.sock`, otherwise `~/.opncap/opncap.sock`). `micro-hook claude-code` forwards a Claude Code hook payload (JSON on stdin) to the daemon. It always exits 0 and prints nothing, so a missing daemon never disturbs Claude Code.

1. Start `opncap-daemon`.
2. Merge `docs/claude-code-hooks.json` into your Claude Code `settings.json`.

Mapping (hook event to LED state): `SessionStart` idle, `UserPromptSubmit` and `PreToolUse` thinking, `PermissionRequest` and `Notification` (`permission_prompt`, `idle_prompt`) input, `Stop` done, `StopFailure` error, `SessionEnd` off. Each Claude Code session gets one of the six agent slots by `session_id`. The status light shows the most urgent state. A session stuck in "thinking" for 120 s falls back to idle, because `Stop` does not fire when you interrupt.

Status: tested with a fake pad and a real Unix socket, **not with a live Claude Code session or a real pad**. The firmware does not drive LEDs yet and answers these commands with `unknown_message`; the daemon logs that and keeps running. Not yet built: `PostToolUseFailure` flash, tray icon, autostart, pinned/recent chat ordering.
