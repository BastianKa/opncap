# SPDX-License-Identifier: Apache-2.0
import io
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from opncap_host import daemon, hook, protocol as p
from opncap_host.client import Client
from opncap_host.engine import DEFAULT_BINDINGS, Engine, HotkeySender, load_bindings

from test_client_cli import FakePad


def key(pos, pressed=1):
    return p.build("key_event", 0, key=pos, pressed=pressed)


def wait_until(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


class ReaderThreadTest(unittest.TestCase):
    def test_events_go_to_callback_and_replies_to_request(self):
        pad = FakePad()
        pad.queue.append(key(7))
        events = []
        c = Client(pad)
        c.start(lambda name, fields: events.append((name, fields)))
        try:
            c.set_state("done")  # reply arrives through the reader thread
            self.assertTrue(wait_until(lambda: events))
        finally:
            c.stop()
        self.assertEqual(events[0], ("key_event", {"key": 7, "pressed": 1}))

    def test_callback_error_does_not_kill_the_reader(self):
        pad = FakePad()
        pad.queue.extend([key(1), key(2)])
        seen = []

        def cb(name, fields):
            seen.append(fields["key"])
            raise RuntimeError("boom")

        c = Client(pad)
        c.start(cb)
        try:
            self.assertTrue(wait_until(lambda: len(seen) == 2))
        finally:
            c.stop()


class FakeController:
    def __init__(self):
        self.decisions = []

    def resolve_permission(self, decision):
        self.decisions.append(decision)
        return True


class EngineTest(unittest.TestCase):
    def test_default_bindings_approve_and_deny(self):
        c = FakeController()
        e = Engine(c)
        e.on_pad_event("key_event", {"key": 7, "pressed": 1})  # K8
        e.on_pad_event("key_event", {"key": 8, "pressed": 1})  # K9
        self.assertEqual(c.decisions, ["allow", "deny"])

    def test_release_and_unbound_keys_do_nothing(self):
        c = FakeController()
        e = Engine(c)
        e.on_pad_event("key_event", {"key": 7, "pressed": 0})
        e.on_pad_event("key_event", {"key": 0, "pressed": 1})
        e.on_pad_event("encoder_event", {"delta": 1})
        self.assertEqual(c.decisions, [])

    def test_hotkey_action(self):
        calls = []
        e = Engine(FakeController(), bindings={"K1": "hotkey:ctrl+shift+k"},
                   hotkeys=HotkeySender(runner=lambda *a, **k: calls.append(a[0]), platform="linux"))
        e.on_pad_event("key_event", {"key": 0, "pressed": 1})
        self.assertEqual(calls, [["xdotool", "key", "ctrl+shift+k"]])

    def test_unsafe_hotkey_is_rejected(self):
        calls = []
        s = HotkeySender(runner=lambda *a, **k: calls.append(a), platform="linux")
        self.assertFalse(s.send("a; rm -rf ~"))
        self.assertEqual(calls, [])

    def test_macos_hotkey(self):
        calls = []
        s = HotkeySender(runner=lambda *a, **k: calls.append(a[0]), platform="darwin")
        self.assertTrue(s.send("cmd+shift+k"))
        self.assertIn("keystroke \"k\" using {command down, shift down}", calls[0][2])

    def test_load_bindings_override(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "b.json"
            f.write_text(json.dumps({"K8": "deny", "K1": "hotkey:f5"}))
            b = load_bindings(f)
        self.assertEqual(b["K8"], "deny")
        self.assertEqual(b["K9"], DEFAULT_BINDINGS["K9"])
        self.assertEqual(load_bindings(Path("/nonexistent/x.json")), DEFAULT_BINDINGS)


def perm(sid="s1"):
    return dict(hook_event_name="PermissionRequest", session_id=sid, cwd="/p", tool_name="Bash")


class PermissionFlowTest(unittest.TestCase):
    def setUp(self):
        self.pad = FakePad()
        self.c = daemon.Controller(open_transport=lambda: self.pad)

    def ask(self, timeout, result):
        result.append(self.c.wait_for_decision(perm(), timeout))

    def test_approve_key_resolves_the_request(self):
        result = []
        t = threading.Thread(target=self.ask, args=(5, result))
        t.start()
        self.assertTrue(wait_until(lambda: self.c._pending))
        self.c.engine.on_pad_event("key_event", {"key": 7, "pressed": 1})  # K8 = approve
        t.join(2)
        self.assertEqual(result, ["allow"])

    def test_deny_key(self):
        result = []
        t = threading.Thread(target=self.ask, args=(5, result))
        t.start()
        self.assertTrue(wait_until(lambda: self.c._pending))
        self.c.engine.on_pad_event("key_event", {"key": 8, "pressed": 1})  # K9 = deny
        t.join(2)
        self.assertEqual(result, ["deny"])

    def test_timeout_gives_no_decision(self):
        result = []
        self.ask(0.05, result)
        self.assertEqual(result, [None])
        self.assertEqual(self.c._pending, [])

    def test_key_without_pending_request(self):
        self.assertFalse(self.c.resolve_permission("allow"))

    def test_request_turns_the_key_orange_then_thinking(self):
        result = []
        t = threading.Thread(target=self.ask, args=(5, result))
        t.start()
        self.assertTrue(wait_until(lambda: self.c._pending))
        self.c.resolve_permission("allow")
        t.join(2)
        states = [p.parse(f)[2].get("state") for f in self.pad.written if p.parse(f)[0] == "set_agent_state"]
        self.assertEqual(states, [p.STATE["input"], p.STATE["thinking"]])


class HookDecisionTest(unittest.TestCase):
    def run_hook(self, decision):
        out = io.StringIO()
        code = hook.main(["claude-code", "--wait", "5"], stdin=io.StringIO(json.dumps(perm())), stdout=out,
                         send=lambda *a, **k: decision)
        return code, out.getvalue()

    def test_allow_prints_decision(self):
        code, out = self.run_hook("allow")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["decision"]["behavior"], "allow")

    def test_deny_prints_message(self):
        d = json.loads(self.run_hook("deny")[1])["hookSpecificOutput"]["decision"]
        self.assertEqual(d["behavior"], "deny")
        self.assertIn("message", d)

    def test_no_decision_prints_nothing(self):
        self.assertEqual(self.run_hook(None), (0, ""))

    def test_wait_ignored_for_other_events(self):
        out = io.StringIO()
        sent = []
        hook.main(["claude-code", "--wait", "5"], stdin=io.StringIO(json.dumps(dict(hook_event_name="Stop", session_id="s"))),
                  stdout=out, send=lambda *a, **k: sent.append(a))
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(len(sent), 1)

    def test_bad_wait_value(self):
        self.assertEqual(hook.main(["claude-code", "--wait", "x"], stdin=io.StringIO("{}")), 2)


class SocketPermissionTest(unittest.TestCase):
    def test_hook_waits_over_the_socket(self):
        pad = FakePad()
        controller = daemon.Controller(open_transport=lambda: pad)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.sock")
            server = daemon.Server(path, controller)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            result = []
            t = threading.Thread(target=lambda: result.append(daemon.send_to_daemon("claude-code", perm(), path, wait=5)))
            t.start()
            try:
                self.assertTrue(wait_until(lambda: controller._pending))
                controller.engine.on_pad_event("key_event", {"key": 7, "pressed": 1})
                t.join(3)
            finally:
                server.shutdown()
                server.server_close()
        self.assertEqual(result, ["allow"])


if __name__ == "__main__":
    unittest.main()
