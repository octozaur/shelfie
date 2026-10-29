import json
import shutil
import unittest
from pathlib import Path

from shelfie import servers
from tests.helpers import TempProject

FIX = Path(__file__).parent / "fixtures"


class DetectBashTest(unittest.TestCase):
    def test_positives(self):
        cases = {
            "npm run dev": None,
            "pnpm dev --port 3001": 3001,
            "npx vite --port 5173": 5173,
            "next dev -p 4000": 4000,
            "python3 -m http.server 8080": 8080,
            "PORT=9000 node server.js": 9000,
            "flutter run -d web-server --web-port 7357": 7357,
            "cd app && npm start": None,
            "yarn run preview --port=4173": 4173,
        }
        for cmd, port in cases.items():
            with self.subTest(cmd=cmd):
                s = servers.detect_bash(cmd, ".")
                self.assertIsNotNone(s)
                self.assertEqual(s["port"], port)
                self.assertEqual(s["command"], cmd)
                self.assertEqual(s["cwd"], ".")

    def test_cd_prefix_sets_cwd(self):
        s = servers.detect_bash("cd app && npm start", ".")
        self.assertEqual(s["cwd"], ".")  # cwd is where the command was issued

    def test_negatives(self):
        for cmd in ["npm test", "npm run build", "git status", "python3 script.py",
                    "ls -la", "echo npm run dev", "grep 'vite' package.json"]:
            with self.subTest(cmd=cmd):
                self.assertIsNone(servers.detect_bash(cmd, "."))


class LaunchJsonTest(unittest.TestCase):
    def test_launch_json_configs(self):
        with TempProject() as root:
            (root / ".claude").mkdir()
            shutil.copy(FIX / "launch.json", root / ".claude" / "launch.json")
            got = servers.from_launch_json(root)
            self.assertEqual(got, [
                {"command": "npm run dev", "cwd": ".", "port": 5173, "name": "web"},
                {"command": "python3 -m http.server 8000", "cwd": ".", "port": 8000, "name": "lab"},
            ])

    def test_missing_or_broken_launch_json(self):
        with TempProject() as root:
            self.assertEqual(servers.from_launch_json(root), [])
            (root / ".claude").mkdir()
            (root / ".claude" / "launch.json").write_text("{nope")
            self.assertEqual(servers.from_launch_json(root), [])

    def test_preview_start_by_name_and_url(self):
        with TempProject() as root:
            (root / ".claude").mkdir()
            shutil.copy(FIX / "launch.json", root / ".claude" / "launch.json")
            s = servers.from_preview_start({"name": "lab"}, root)
            self.assertEqual(s["port"], 8000)
            self.assertEqual(s["command"], "python3 -m http.server 8000")
            s = servers.from_preview_start({"url": "http://localhost:3000/x"}, root)
            self.assertEqual(s, {"command": None, "cwd": ".", "port": 3000})
            self.assertIsNone(servers.from_preview_start({"url": "https://example.com"}, root))
            self.assertIsNone(servers.from_preview_start({"name": "nope"}, root))


class PublishInfoTest(unittest.TestCase):
    def test_publish_info_from_response(self):
        p = json.loads((FIX / "artifact_publish.json").read_text())
        url, src, title = servers.publish_info(p["tool_input"], p["tool_response"])
        self.assertEqual(url, "https://claude.ai/code/artifact/ab12-cd34")
        self.assertEqual(src, "brief.html")
        self.assertIsNone(title)

    def test_publish_info_url_input_and_title(self):
        url, src, title = servers.publish_info(
            {"file_path": "a.html", "url": "https://claude.ai/artifact/DemoLab123", "title": "Lab"}, "ok")
        self.assertEqual(url, "https://claude.ai/artifact/DemoLab123")
        self.assertEqual(title, "Lab")

    def test_typed_artifact_create(self):
        url, src, title = servers.publish_info(
            {"type_url": "https://claude.ai/artifact/type-slides", "title": "Q4 deck"},
            "Created https://claude.ai/artifact/NewDeck123")
        self.assertEqual(url, "https://claude.ai/artifact/NewDeck123")
        self.assertIsNone(src)
        self.assertEqual(title, "Q4 deck")

    def test_non_publish_actions(self):
        self.assertEqual(servers.publish_info({"action": "list"}, "https://claude.ai/artifact/x"),
                         (None, None, None))
        self.assertEqual(servers.publish_info({"action": "read", "url": "https://claude.ai/artifact/x"}, ""),
                         (None, None, None))
        self.assertEqual(servers.publish_info({"asset": True, "url": "https://claude.ai/artifact/x",
                                               "file_path": "a.png"}, ""), (None, None, None))
        self.assertEqual(servers.publish_info({"action": "publish", "file_path": "a.html"}, "error"),
                         (None, None, None))


if __name__ == "__main__":
    unittest.main()
