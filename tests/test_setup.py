import json
import os
import unittest

from shelfie import setup, store
from tests.helpers import TempProject

PLUGIN = "/opt/plugins/shelfie 1.0"


class SetupTest(unittest.TestCase):
    def test_setup_writes_config_launcher_and_dashboard(self):
        with TempProject() as root:
            setup.run_setup(root, ["html", "pdf"], False, plugin_root=PLUGIN)
            self.assertEqual(store.load_config(root)["formats"], ["html", "pdf"])
            launcher = root / ".shelfie" / "bin" / "shelfie"
            text = launcher.read_text()
            self.assertIn(f"'{PLUGIN}/bin/shelfie'", text)
            self.assertIn(f"CLAUDE_PROJECT_DIR={root}", text)
            self.assertTrue(os.access(launcher, os.X_OK))
            self.assertTrue((root / ".shelfie" / "shelfie.html").exists())

    def test_launcher_survives_hostile_project_names(self):
        import subprocess
        for name in ['p$(echo PWNED >&2)', 'q"uote', 'cost$HOME', "it's"]:
            with self.subTest(name=name), TempProject(name) as root:
                setup.run_setup(root, ["html"], False)
                r = subprocess.run([str(root / ".shelfie" / "bin" / "shelfie"), "formats"],
                                   capture_output=True, text=True, cwd=root)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertNotIn("PWNED", r.stderr)
                self.assertIn("✓ html", r.stdout)

    def test_setup_keeps_existing_excludes(self):
        with TempProject() as root:
            store.save_config(root, {"version": 1, "formats": ["md"], "exclude": ["drafts/*"]})
            setup.run_setup(root, ["html"], False, plugin_root=PLUGIN)
            self.assertEqual(store.load_config(root)["exclude"], ["drafts/*"])

    def test_setup_without_permission_leaves_settings_untouched(self):
        with TempProject() as root:
            setup.run_setup(root, ["html"], False, plugin_root=PLUGIN)
            self.assertFalse((root / ".claude" / "settings.local.json").exists())

    def test_setup_merges_settings_local(self):
        with TempProject() as root:
            (root / ".claude").mkdir()
            f = root / ".claude" / "settings.local.json"
            f.write_text(json.dumps({"permissions": {"allow": ["Bash(npm test:*)"], "deny": ["Read(.env)"]},
                                     "env": {"A": "1"}}))
            setup.run_setup(root, ["html"], True, plugin_root=PLUGIN)
            setup.run_setup(root, ["html"], True, plugin_root=PLUGIN)
            data = json.loads(f.read_text())
            self.assertEqual(data["env"], {"A": "1"})
            self.assertEqual(data["permissions"]["deny"], ["Read(.env)"])
            self.assertEqual(data["permissions"]["allow"], [
                "Bash(npm test:*)",
                f"Bash({root}/.shelfie/bin/shelfie note:*)",
            ])

    def test_setup_creates_settings_local(self):
        with TempProject() as root:
            setup.run_setup(root, ["html"], True, plugin_root=PLUGIN)
            data = json.loads((root / ".claude" / "settings.local.json").read_text())
            self.assertEqual(data["permissions"]["allow"], [f"Bash({root}/.shelfie/bin/shelfie note:*)"])

    def test_set_formats(self):
        with TempProject() as root:
            setup.run_setup(root, ["html", "pdf"], False, plugin_root=PLUGIN)
            got = setup.set_formats(root, enable=["image", "md"], disable=["pdf"])
            self.assertEqual(got, ["html", "md", "image"])
            self.assertEqual(store.load_config(root)["formats"], ["html", "md", "image"])

    def test_unknown_format_rejected(self):
        with TempProject() as root:
            with self.assertRaises(ValueError):
                setup.run_setup(root, ["htm"], False, plugin_root=PLUGIN)

    def test_setup_context_mentions_command(self):
        text = setup.setup_context(PLUGIN)
        self.assertIn(f'"{PLUGIN}/bin/shelfie" setup --formats', text)
        self.assertIn("settings.local.json", text)


if __name__ == "__main__":
    unittest.main()
