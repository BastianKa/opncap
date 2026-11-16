<!-- SPDX-License-Identifier: Apache-2.0 -->
# Live test with Claude Code (no pad needed)

Goal: check that Claude Code sends the hook events and fields the adapter expects. The daemon runs in `--debug` mode and logs every event and the state it maps to. Without a pad it also logs `pad not available`; that is fine for this test.

## 1. Install

```sh
cd software/host
python3 -m venv ~/.venvs/opncap && . ~/.venvs/opncap/bin/activate
pip install .                      # installs opncap-daemon, micro-hook, micro-state
```

`pip install` also pulls the `hid` package; on Linux it needs the system library (`sudo apt install libhidapi-hidraw0`). For this test it does not matter if `hid` cannot find a pad.

## 2. Start the daemon

```sh
opncap-daemon --debug
```

Leave it running in its own terminal. It prints `listening on .../opncap.sock`.

## 3. Add the hooks

Merge the `hooks` block of `docs/claude-code-hooks.json` into `~/.claude/settings.json` (user-wide) or `.claude/settings.local.json` (one project). Use the absolute path of `micro-hook` (`which micro-hook`) in the `command` fields if Claude Code does not find it on its PATH. Then start a **new** Claude Code session so the hooks are loaded.

## 4. Things to try, and what the daemon log should show

| Do this in Claude Code | Expected log line (`-> state`) |
|---|---|
| Start the session | `'SessionStart' ... -> idle` |
| Send a prompt | `'UserPromptSubmit' ... -> thinking`, then `'PreToolUse'` lines for each tool |
| Let the answer finish | `'Stop' ... -> done` |
| Ask for something that needs permission (for example run a shell command) | `'PermissionRequest' ... -> input`, and the daemon waits up to 25 s |
| Leave Claude Code idle at the prompt for a while | a `'Notification' notification_type='idle_prompt' ... -> input` |
| Interrupt a running answer with Esc | no `Stop` line (expected); after 120 s the session falls back to idle |
| Exit the session | `'SessionEnd' ... -> end` |
| Open two sessions in two terminals | different `session=` prefixes |

## 5. What to report back

Please send the log, and answer:
1. Does every event in the table appear, with the name shown? Which are missing or named differently?
2. Does `Notification` carry `notification_type`? Which values do you see (`permission_prompt`, `idle_prompt`, others)?
3. On a permission prompt: does the terminal prompt appear immediately, or only after the 25 s wait? (The hook blocks while the daemon waits for a pad key. Without a pad that means a 25 s delay each time; set `--wait 2` in the hook command to shorten it for this test.)
4. Anything printed in the Claude Code terminal by the hooks (errors, warnings)?

## 6. Remove the test

Delete the hooks block from `settings.json` again and stop the daemon with `Ctrl+C`.
