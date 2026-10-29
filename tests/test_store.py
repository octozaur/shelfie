import json
import multiprocessing
import os
import unittest
from pathlib import Path

from shelfie import store
from tests.helpers import TempProject


def _writer(root, n):
    for i in range(n):
        with store.locked_registry(Path(root)) as reg:
            reg["entries"].append({"id": store.new_id(), "i": i})


class StoreTest(unittest.TestCase):
    def test_project_root_from_env(self):
        with TempProject() as root:
            self.assertEqual(store.project_root(), root)

    def test_missing_config_is_none(self):
        with TempProject() as root:
            self.assertIsNone(store.load_config(root))

    def test_config_roundtrip(self):
        with TempProject() as root:
            store.save_config(root, {"version": 1, "formats": ["pdf"], "exclude": []})
            self.assertEqual(store.load_config(root)["formats"], ["pdf"])

    def test_registry_roundtrip_unicode(self):
        with TempProject("proj with space") as root:
            with store.locked_registry(root) as reg:
                reg["entries"].append({"id": "a", "path": "звіти/план.md",
                                       "title": "Звіт — Q4 ✓"})
            reg = store.read_registry(root)
            self.assertEqual(reg["entries"][0]["path"], "звіти/план.md")
            self.assertEqual(reg["entries"][0]["title"], "Звіт — Q4 ✓")

    def test_empty_registry(self):
        with TempProject() as root:
            self.assertEqual(store.read_registry(root), {"version": 1, "entries": []})

    def test_new_id(self):
        ids = {store.new_id() for _ in range(200)}
        self.assertEqual(len(ids), 200)
        for i in ids:
            self.assertRegex(i, r"^[0-9a-z]{6}$")

    def test_now_iso_has_offset(self):
        self.assertRegex(store.now_iso(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_concurrent_writers(self):
        with TempProject() as root:
            ctx = multiprocessing.get_context("spawn")
            procs = [ctx.Process(target=_writer, args=(str(root), 25)) for _ in range(8)]
            for p in procs:
                p.start()
            for p in procs:
                p.join()
            data = json.loads((root / ".shelfie" / "registry.json").read_text("utf-8"))
            self.assertEqual(len(data["entries"]), 200)

    def test_log_error(self):
        with TempProject() as root:
            try:
                raise ValueError("boom")
            except ValueError as e:
                store.log_error(root, e)
            self.assertIn("boom", (root / ".shelfie" / "errors.log").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
