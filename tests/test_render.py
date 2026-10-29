import json
import re
import unittest

from shelfie import ingest, notes, render, store
from tests.helpers import TempProject

ALL = ["artifact", "html", "pdf", "md", "doc", "slides", "sheet", "server", "image"]


def setup_project(root, formats=ALL):
    store.save_config(root, {"version": 1, "formats": formats, "exclude": []})


def add(root, path, title, t="html", create=True):
    if create:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("x")
    with store.locked_registry(root) as reg:
        e = ingest.record_file(reg, {"path": path, "type": t, "files": None}, "s1")
        notes.apply_note(reg, e["id"], True, title, "Desc", None)
        return e["id"]


def data_block(html):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    return m.group(1)


class RenderTest(unittest.TestCase):
    def test_render_writes_file_with_data(self):
        with TempProject("Proj One") as root:
            setup_project(root)
            add(root, "звіт.html", "Звіт — Q4")
            out = render.render(root)
            self.assertEqual(out, root / ".shelfie" / "shelfie.html")
            html = out.read_text("utf-8")
            data = json.loads(data_block(html))
            self.assertEqual(data["project"], "Proj One")
            self.assertEqual(data["entries"][0]["title"], "Звіт — Q4")
            self.assertTrue(data["entries"][0]["exists"])
            self.assertTrue(data["entries"][0]["abs_path"].endswith("звіт.html"))
            self.assertIn("html", data["types"])

    def test_script_breaking_text_is_escaped(self):
        nasty = '</script><b>x"\' 🎉'
        with TempProject() as root:
            setup_project(root)
            add(root, "a.html", nasty)
            html = render.render(root).read_text("utf-8")
            block = data_block(html)
            self.assertNotIn("</script><b>", block)
            self.assertEqual(json.loads(block)["entries"][0]["title"], nasty)

    def test_no_external_requests(self):
        with TempProject() as root:
            setup_project(root)
            html = render.render(root).read_text("utf-8")
            self.assertNotRegex(html, r"<script[^>]+src=")
            self.assertNotRegex(html, r'<link[^>]+href="http')
            self.assertNotIn("@import", html)

    def test_untrusted_urls_and_ports_dropped(self):
        with TempProject() as root:
            setup_project(root)
            with store.locked_registry(root) as reg:
                reg["entries"] += [
                    {"id": "x1", "type": "artifact", "status": "artifact", "title": "Evil", "url": "javascript:alert(1)",
                     "path": None, "server": None, "files": None, "changes": [],
                     "created_at": "2026-10-01T10:00:00+00:00", "updated_at": "2026-10-01T10:00:00+00:00"},
                    {"id": "x2", "type": "server", "status": "artifact", "title": "Srv", "url": None, "path": None,
                     "server": {"command": "npm run dev", "cwd": ".", "port": "1@evil.com"}, "files": None,
                     "changes": [], "created_at": "2026-10-01T10:00:00+00:00",
                     "updated_at": "2026-10-01T10:00:00+00:00"},
                    {"id": "x3", "type": "artifact", "status": "artifact", "title": "Ok",
                     "url": "https://claude.ai/artifact/abc", "path": None, "server": None, "files": None,
                     "changes": [], "created_at": "2026-10-01T10:00:00+00:00",
                     "updated_at": "2026-10-01T10:00:00+00:00"},
                ]
            data = json.loads(data_block(render.render(root).read_text("utf-8")))
            by = {e["id"]: e for e in data["entries"]}
            self.assertIsNone(by["x1"]["url"])
            self.assertIsNone(by["x2"]["server"]["port"])
            self.assertEqual(by["x3"]["url"], "https://claude.ai/artifact/abc")

    def test_disabled_type_hidden(self):
        with TempProject() as root:
            setup_project(root, ["html"])
            add(root, "a.html", "Shown")
            add(root, "b.pdf", "Hidden", t="pdf")
            data = json.loads(data_block(render.render(root).read_text("utf-8")))
            self.assertEqual([e["title"] for e in data["entries"]], ["Shown"])
            self.assertEqual(list(data["types"]), ["html"])

    def test_merged_artifact_shown_when_source_type_disabled(self):
        with TempProject() as root:
            setup_project(root, ["artifact"])
            with store.locked_registry(root) as reg:
                ingest.record_file(reg, {"path": "a.html", "type": "html", "files": None}, "s1")
                ingest.record_published(reg, "https://claude.ai/artifact/x", "a.html", None, "s1")
            data = json.loads(data_block(render.render(root).read_text("utf-8")))
            self.assertEqual(len(data["entries"]), 1)

    def test_missing_file_flagged(self):
        with TempProject() as root:
            setup_project(root)
            add(root, "gone.pdf", "Gone", t="pdf", create=False)
            data = json.loads(data_block(render.render(root).read_text("utf-8")))
            self.assertFalse(data["entries"][0]["exists"])

    def test_group_exists_if_any_file_exists(self):
        with TempProject() as root:
            setup_project(root)
            (root / "lv").mkdir()
            (root / "lv" / "1.html").write_text("x")
            with store.locked_registry(root) as reg:
                ingest.record_file(reg, {"path": "lv/", "type": "html",
                                         "files": ["lv/1.html", "lv/2.html"]}, "s1")
            data = json.loads(data_block(render.render(root).read_text("utf-8")))
            self.assertTrue(data["entries"][0]["exists"])


if __name__ == "__main__":
    unittest.main()
