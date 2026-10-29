from __future__ import annotations

import os
import shutil
import subprocess
import time
import unittest
from pathlib import Path

from shelfie import scan
from tests.helpers import TempProject

ALL = ["artifact", "html", "pdf", "md", "doc", "slides", "sheet", "server", "image"]


def touch(root: Path, rel: str, mtime: float | None = None) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    if mtime is not None:
        os.utime(p, (mtime, mtime))


class TurnStateTest(unittest.TestCase):
    def test_mark_and_read_turn_start(self):
        with TempProject() as root:
            self.assertIsNone(scan.turn_start(root, "s1"))
            scan.mark_turn_start(root, "s1", at=123.5)
            self.assertEqual(scan.turn_start(root, "s1"), 123.5)
            self.assertIsNone(scan.turn_start(root, "s2"))


class ChangedFilesTest(unittest.TestCase):
    def test_only_files_in_window(self):
        with TempProject() as root:
            now = time.time()
            touch(root, "old.html", now - 100)
            touch(root, "new.html", now)
            self.assertEqual(scan.changed_files(root, now - 10, ALL, []), ["new.html"])

    def test_disabled_format_ignored(self):
        with TempProject() as root:
            touch(root, "a.pdf")
            touch(root, "b.html")
            self.assertEqual(scan.changed_files(root, 0, ["html"], []), ["b.html"])

    def test_excluded_dirs_and_globs(self):
        with TempProject() as root:
            for rel in ["node_modules/x/a.html", ".venv/b.html", "drafts/c.md",
                        ".shelfie/shelfie.html", "keep/d.md"]:
                touch(root, rel)
            self.assertEqual(scan.changed_files(root, 0, ALL, ["drafts/*"]), ["keep/d.md"])

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_gitignore_respected(self):
        with TempProject() as root:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text("out/\n")
            touch(root, "out/x.html")
            touch(root, "in/y.html")
            self.assertEqual(scan.changed_files(root, 0, ALL, []), ["in/y.html"])

    def test_big_tree_is_fast(self):
        with TempProject() as root:
            for i in range(5000):
                touch(root, f"node_modules/p{i % 50}/f{i}.html")
            for i in range(50):
                touch(root, f"site/p{i}.html")
            t = time.time()
            found = scan.changed_files(root, 0, ALL, [])
            self.assertLess(time.time() - t, 1.0)
            self.assertEqual(len(found), 50)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_cap_applies_after_filtering(self):
        with TempProject() as root:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            for i in range(scan.MAX_FILES + 5):
                (root / "aaa").mkdir(exist_ok=True)
                (root / "aaa" / f"f{i}.txt").write_text("")
            touch(root, "zzz/report.html")
            self.assertEqual(scan.changed_files(root, 0, ALL, []), ["zzz/report.html"])

    def test_unicode_names(self):
        with TempProject("proj with space") as root:
            touch(root, "звіти/план.md")
            self.assertEqual(scan.changed_files(root, 0, ALL, []), ["звіти/план.md"])


class GroupNewTest(unittest.TestCase):
    def test_grouping(self):
        paths = [f"levels/l{i:02}.html" for i in range(74)] + ["report.html"]
        cands = scan.group_new(paths, set())
        self.assertEqual(len(cands), 2)
        group = next(c for c in cands if c["path"] == "levels/")
        self.assertEqual(len(group["files"]), 74)
        self.assertEqual(group["type"], "html")
        single = next(c for c in cands if c["path"] == "report.html")
        self.assertIsNone(single["files"])

    def test_below_threshold_not_grouped(self):
        paths = [f"img/{i}.png" for i in range(4)]
        self.assertEqual(len(scan.group_new(paths, set())), 4)

    def test_known_paths_never_grouped(self):
        paths = [f"img/{i}.png" for i in range(6)]
        cands = scan.group_new(paths, {"img/0.png"})
        self.assertIn({"path": "img/0.png", "type": "image", "files": None}, cands)
        group = next(c for c in cands if c["path"] == "img/")
        self.assertEqual(len(group["files"]), 5)

    def test_root_dir_group(self):
        cands = scan.group_new([f"{i}.png" for i in range(5)], set())
        self.assertEqual(cands[0]["path"], "./")


if __name__ == "__main__":
    unittest.main()
