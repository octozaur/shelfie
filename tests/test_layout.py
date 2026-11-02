import json
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


class LayoutTest(unittest.TestCase):
    def test_no_top_level_bin_dir(self):
        # claude.ai rejects a plugin with a top-level bin/ directory
        self.assertFalse((PLUGIN / "bin").exists())

    def test_hooks_point_at_existing_entry(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        for groups in hooks.values():
            for group in groups:
                for h in group["hooks"]:
                    rel = h["command"].split('"${CLAUDE_PLUGIN_ROOT}/', 1)[1].split('"', 1)[0]
                    self.assertTrue((PLUGIN / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
