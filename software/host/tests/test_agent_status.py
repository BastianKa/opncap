# SPDX-License-Identifier: Apache-2.0
import io
import json
import os
import tempfile
import threading
import unittest

from opncap_host import daemon, hook, protocol as p
from opncap_host.adapters import claude_code
from opncap_host.sessions import SessionRegistry

from test_client_cli import FakePad


def ev(name, sid="s1", **extra):
    return dict(hook_event_name=name, session_id=sid, cwd="/proj", **extra)


class AdapterTest(unittest.TestCase):
    def test_mapping(self):
        cases = [("SessionStart", {}, "idle"), ("UserPromptSubmit", {}, "thinking"), ("PreToolUse", {}, "thinking"),
                 ("PermissionRequest", {}, "input"), ("Stop", {}, "done"), ("StopFailure", {}, "error"),
                 ("SessionEnd", {}, claude_code.END),
                 ("Notification", {"notification_type": "permission_prompt"}, "input"),
                 ("Notification", {"notification_type": "idle_prompt"}, "input")]
        for name, extra, state in cases:
            with self.subTest(name, extra=extra):
                self.assertEqual(claude_code.map_event(ev(name, **extra)), ("s1", "/proj", state))

    def test_ignored(self):
        self.assertIsNone(claude_code.map_event(ev("Notification", notification_type="auth_success")))
        self.assertIsNone(claude_code.map_event(ev("PostToolUseFailure")))
        self.assertIsNone(claude_code.map_event({"hook_event_name": "Stop"}))  # no session_id
        self.assertIsNone(claude_code.map_event({}))


class RegistryTest(unittest.TestCase):
    def test_slots_follow_sessions(self):
        r = SessionRegistry()
        self.assertEqual(r.update("a", "/a", "idle"), [(0, "idle")])
        self.assertEqual(r.update("b", "/b", "thinking"), [(1, "thinking")])
        self.assertEqual(r.update("a", "/a", "done"), [(0, "done")])
        self.assertEqual(r.update("a", "/a", "done"), [])  # no change, nothing to send
        self.assertEqual(r.end("a"), [(0, "off")])
        self.assertEqual(r.update("c", "/c", "idle"), [(0, "idle")])  # slot 0 is free again

    def test_overall_priority(self):
        r = SessionRegistry()
        self.assertEqual(r.overall(), "off")
        r.update("a", "", "done")
        r.update("b", "", "thinking")
        self.assertEqual(r.overall(), "thinking")
        r.update("c", "", "input")
        self.assertEqual(r.overall(), "input")
        r.update("d", "", "error")
        self.assertEqual(r.overall(), "error")

    def test_seventh_session_replaces_the_least_urgent(self):
        r = SessionRegistry()
        for i in range(6):
            r.update(f"s{i}", "", "input" if i else "idle")
        self.assertEqual(r.update("new", "", "thinking"), [(0, "thinking")])  # slot of the idle one

    def test_stale_thinking_falls_back_to_idle(self):
        now = [0.0]
        r = SessionRegistry(clock=lambda: now[0], stale_after=10)
        r.update("a", "", "thinking")
        now[0] = 5
        self.assertEqual(r.expire(), [])
        now[0] = 11
        self.assertEqual(r.expire(), [(0, "idle")])


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.pad = FakePad()
        self.logs = []
        self.c = daemon.Controller(open_transport=lambda: self.pad, log=self.logs.append)

    def sent(self):
        return [p.parse(f)[0::2] for f in self.pad.written]  # (name, fields)

    def test_prompt_then_stop(self):
        self.c.handle("claude-code", ev("UserPromptSubmit"))
        self.c.handle("claude-code", ev("Stop"))
        self.assertEqual(self.sent(), [
            ("set_agent_state", {"slot": 0, "state": p.STATE["thinking"]}), ("set_state", {"state": p.STATE["thinking"]}),
            ("set_agent_state", {"slot": 0, "state": p.STATE["done"]}), ("set_state", {"state": p.STATE["done"]}),
        ])

    def test_irrelevant_event_sends_nothing(self):
        self.c.handle("claude-code", ev("PostToolUse"))
        self.assertEqual(self.pad.written, [])

    def test_session_end_turns_slot_off(self):
        self.c.handle("claude-code", ev("SessionStart"))
        self.c.handle("claude-code", ev("SessionEnd"))
        self.assertEqual(self.sent()[-2:], [("set_agent_state", {"slot": 0, "state": p.STATE["off"]}),
                                            ("set_state", {"state": p.STATE["off"]})])

    def test_no_pad_is_not_an_error(self):
        from opncap_host.transport import DeviceNotFound

        def missing():
            raise DeviceNotFound("no opncap pad found")

        c = daemon.Controller(open_transport=missing, log=self.logs.append)
        c.handle("claude-code", ev("Stop"))
        self.assertTrue(any("not available" in m for m in self.logs))

    def test_firmware_without_led_support_is_logged(self):
        self.pad.ack_status = 1  # unknown_message
        self.c.handle("claude-code", ev("Stop"))
        self.assertTrue(any("rejected" in m for m in self.logs))

    def test_debug_logs_every_event_even_without_a_pad(self):
        from opncap_host.transport import DeviceNotFound

        def missing():
            raise DeviceNotFound("no pad")

        c = daemon.Controller(open_transport=missing, log=self.logs.append)
        c.debug = True
        c.handle("claude-code", ev("Notification", notification_type="idle_prompt"))
        c.handle("claude-code", ev("PostToolUse"))
        self.assertTrue(any("'Notification'" in m and "-> input" in m for m in self.logs))
        self.assertTrue(any("'PostToolUse'" in m and "ignored" in m for m in self.logs))

    def test_unknown_source_is_ignored(self):
        self.c.handle("other", ev("Stop"))
        self.assertEqual(self.pad.written, [])


class SocketTest(unittest.TestCase):
    def test_hook_to_daemon_roundtrip(self):
        pad = FakePad()
        controller = daemon.Controller(open_transport=lambda: pad)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.sock")
            server = daemon.Server(path, controller)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                payload = ev("UserPromptSubmit")
                self.assertTrue(daemon.send_to_daemon("claude-code", payload, path))
                for _ in range(100):
                    if pad.written:
                        break
                    threading.Event().wait(0.02)
            finally:
                server.shutdown()
                server.server_close()
        self.assertEqual(p.parse(pad.written[0])[0], "set_agent_state")

    def test_hook_without_daemon_exits_quietly(self):
        stdin = io.StringIO(json.dumps(ev("Stop")))
        os.environ["XDG_RUNTIME_DIR"] = tempfile.mkdtemp()
        self.assertEqual(hook.main(["claude-code"], stdin=stdin), 0)

    def test_hook_ignores_garbage_input(self):
        self.assertEqual(hook.main(["claude-code"], stdin=io.StringIO("not json")), 0)


if __name__ == "__main__":
    unittest.main()
