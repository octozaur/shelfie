import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

from shelfie import store
from tests.helpers import TempProject

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin" / "shelfie"
FIX = Path(__file__).parent / "fixtures"


def run(root, args, stdin=""):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), CLAUDE_PLUGIN_ROOT=str(REPO))
    return subprocess.run([sys.executable, str(BIN)] + args, input=stdin, text=True,
                          capture_output=True, env=env, cwd=root, timeout=30)


def hook(root, event, payload):
    return run(root, ["hook", event], json.dumps(payload))


class HooksTest(unittest.TestCase):
    def test_malformed_stdin_exits_zero(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            before = store.read_registry(root)
            for stdin in ["", "{", '{"tool_name":"Artifact"}', "[]", '{"tool_name":"Bash","tool_input":null}']:
                with self.subTest(stdin=stdin):
                    r = run(root, ["hook", "post_tool"], stdin)
                    self.assertEqual(r.returncode, 0)
                    self.assertEqual(r.stdout, "")
            self.assertEqual(store.read_registry(root), before)

    def test_malformed_config_exits_zero(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            (root / ".shelfie" / "config.json").write_text("{broken")
            for event in ["session_start", "prompt_submit", "post_tool", "stop"]:
                with self.subTest(event=event):
                    r = hook(root, event, {"session_id": "s1", "tool_name": "Bash",
                                           "tool_input": {"command": "npm run dev"}})
                    self.assertEqual(r.returncode, 0)
                    self.assertEqual(r.stdout, "")
                    self.assertEqual(r.stderr, "")

    def test_unknown_event_exits_zero(self):
        with TempProject() as root:
            self.assertEqual(run(root, ["hook", "nope"], "{}").returncode, 0)

    def test_unconfigured_project_noop(self):
        with TempProject() as root:
            (root / "a.html").write_text("x")
            hook(root, "prompt_submit", {"session_id": "s1"})
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            self.assertEqual(r.stdout, "")
            r = hook(root, "post_tool", {"session_id": "s1", "tool_name": "Bash",
                                         "tool_input": {"command": "npm run dev"}, "cwd": str(root)})
            self.assertFalse((root / ".shelfie" / "registry.json").exists())
            r = hook(root, "session_start", {"session_id": "s1"})
            out = json.loads(r.stdout)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("setup --formats", out["hookSpecificOutput"]["additionalContext"])

    def test_session_start_configured_refreshes_launcher(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            (root / ".shelfie" / "bin" / "shelfie").unlink()
            r = hook(root, "session_start", {"session_id": "s1"})
            self.assertEqual(r.stdout, "")
            self.assertTrue((root / ".shelfie" / "bin" / "shelfie").exists())

    def test_full_turn(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            hook(root, "prompt_submit", {"session_id": "s1"})
            (root / "report.pdf").write_text("x")
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            out = json.loads(r.stdout)
            self.assertEqual(out["decision"], "block")
            eid = store.read_registry(root)["entries"][0]["id"]
            self.assertIn(eid, out["reason"])
            r = subprocess.run([str(root / ".shelfie" / "bin" / "shelfie"), "note", eid, "--artifact", "yes",
                                "--title", "Q4 report", "--desc", "Numbers for the board."],
                               cwd=root, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": True})
            self.assertEqual(r.stdout, "")
            self.assertIn("Q4 report", (root / ".shelfie" / "shelfie.html").read_text("utf-8"))
            # nothing pending now → plain stop is silent too
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            self.assertEqual(r.stdout, "")

    def test_file_before_turn_not_captured(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            f = root / "old.html"
            f.write_text("x")
            past = time.time() - 60
            os.utime(f, (past, past))
            hook(root, "prompt_submit", {"session_id": "s1"})
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            self.assertEqual(r.stdout, "")
            self.assertEqual(store.read_registry(root)["entries"], [])

    def test_edits_between_turns_not_captured(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            hook(root, "prompt_submit", {"session_id": "s1"})
            hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            (root / "manual.html").write_text("x")
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            self.assertEqual(r.stdout, "")
            self.assertEqual(store.read_registry(root)["entries"], [])

    def test_interrupted_turn_files_still_captured(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            hook(root, "prompt_submit", {"session_id": "s1"})
            (root / "made-before-esc.pdf").write_text("x")
            time.sleep(1.2)
            hook(root, "prompt_submit", {"session_id": "s1"})  # no Stop in between (user hit Esc)
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            self.assertIn("made-before-esc.pdf", r.stdout)

    def test_stop_without_turn_start_scans_nothing(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            (root / "a.html").write_text("x")
            r = hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            self.assertEqual(r.stdout, "")

    def test_publish_then_stop_single_entry(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            hook(root, "prompt_submit", {"session_id": "sess-1"})
            (root / "brief.html").write_text("x")
            payload = json.loads((FIX / "artifact_publish.json").read_text())
            payload["cwd"] = str(root)
            hook(root, "post_tool", payload)
            hook(root, "stop", {"session_id": "sess-1", "stop_hook_active": False})
            entries = store.read_registry(root)["entries"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["type"], "artifact")
            self.assertEqual(entries[0]["url"], "https://claude.ai/code/artifact/ab12-cd34")
            self.assertEqual(entries[0]["path"], "brief.html")

    def test_publish_outside_project_has_no_path(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            payload = json.loads((FIX / "artifact_publish.json").read_text())
            payload["tool_input"]["file_path"] = "/tmp/elsewhere/brief.html"
            hook(root, "post_tool", payload)
            e = store.read_registry(root)["entries"][0]
            self.assertIsNone(e["path"])

    def test_bash_server_and_disabled_type(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "html", "--allow-permission", "no"])
            hook(root, "post_tool", {"session_id": "s1", "tool_name": "Bash", "cwd": str(root),
                                     "tool_input": {"command": "npm run dev"}})
            self.assertEqual(store.read_registry(root)["entries"], [])
            run(root, ["formats", "--enable", "server"])
            hook(root, "post_tool", {"session_id": "s1", "tool_name": "Bash", "cwd": str(root / "app"),
                                     "tool_input": {"command": "npm run dev -- --port 3000"}})
            e = store.read_registry(root)["entries"][0]
            self.assertEqual(e["server"], {"command": "npm run dev -- --port 3000", "cwd": "app", "port": 3000})

    def test_launch_json_write(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            (root / ".claude").mkdir(exist_ok=True)
            (root / ".claude" / "launch.json").write_text((FIX / "launch.json").read_text())
            hook(root, "post_tool", {"session_id": "s1", "tool_name": "Write", "cwd": str(root),
                                     "tool_input": {"file_path": str(root / ".claude" / "launch.json")}})
            self.assertEqual(len(store.read_registry(root)["entries"]), 2)

    def test_cli_ignore_restore_list(self):
        with TempProject() as root:
            run(root, ["setup", "--formats", "all", "--allow-permission", "no"])
            hook(root, "prompt_submit", {"session_id": "s1"})
            (root / "README.md").write_text("x")
            hook(root, "stop", {"session_id": "s1", "stop_hook_active": False})
            eid = store.read_registry(root)["entries"][0]["id"]
            self.assertEqual(run(root, ["note", eid, "--artifact", "no"]).returncode, 0)
            self.assertIn(eid, run(root, ["list", "--ignored"]).stdout)
            self.assertNotIn(eid, run(root, ["list"]).stdout)
            self.assertEqual(run(root, ["restore", eid]).returncode, 0)
            self.assertIn(eid, run(root, ["list"]).stdout)
            r = run(root, ["note", "zzzzzz", "--artifact", "yes"])
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
