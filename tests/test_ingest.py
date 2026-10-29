import unittest

from shelfie import ingest


def reg():
    return {"version": 1, "entries": []}


def cand(path, t="html", files=None):
    return {"path": path, "type": t, "files": files}


class IngestTest(unittest.TestCase):
    def test_new_file_is_pending_new(self):
        r = reg()
        e = ingest.record_file(r, cand("a.html"), "s1")
        self.assertEqual(e["status"], "pending")
        self.assertEqual(e["pending"]["kind"], "new")
        self.assertEqual(e["pending"]["session"], "s1")
        self.assertEqual(e["type"], "html")
        self.assertEqual(e["changes"], [])
        self.assertEqual(len(r["entries"]), 1)

    def test_same_file_twice_is_one_entry(self):
        r = reg()
        ingest.record_file(r, cand("a.html"), "s1")
        e = ingest.record_file(r, cand("a.html"), "s1")
        self.assertEqual(len(r["entries"]), 1)
        self.assertEqual(e["pending"]["kind"], "new")

    def _noted(self, r, session="s1", **kw):
        e = ingest.record_file(r, cand("a.html"), session)
        e.update(status="artifact", pending=None, noted_sessions=[session], title="A")
        return e

    def test_change_in_noted_session_does_not_ask(self):
        r = reg()
        self._noted(r)
        e = ingest.record_file(r, cand("a.html"), "s1")
        self.assertIsNone(e["pending"])

    def test_change_in_new_session_asks_changed(self):
        r = reg()
        self._noted(r)
        e = ingest.record_file(r, cand("a.html"), "s2")
        self.assertEqual(e["pending"]["kind"], "changed")
        self.assertEqual(e["pending"]["session"], "s2")

    def test_ignored_never_pending(self):
        r = reg()
        e = self._noted(r)
        e["status"] = "ignored"
        old = e["updated_at"]
        e2 = ingest.record_file(r, cand("a.html"), "s9")
        self.assertIsNone(e2["pending"])
        self.assertEqual(e2["status"], "ignored")
        self.assertGreaterEqual(e2["updated_at"], old)

    def test_publish_merges_with_file(self):
        r = reg()
        ingest.record_file(r, cand("brief.html"), "s1")
        e = ingest.record_published(r, "https://claude.ai/code/artifact/x1", "brief.html", "Brief", "s1")
        self.assertEqual(len(r["entries"]), 1)
        self.assertEqual(e["type"], "artifact")
        self.assertEqual(e["source_type"], "html")
        self.assertEqual(e["url"], "https://claude.ai/code/artifact/x1")
        self.assertEqual(e["path"], "brief.html")

    def test_file_after_publish_matches_same_entry(self):
        r = reg()
        ingest.record_published(r, "https://claude.ai/artifact/x1", "brief.html", None, "s1")
        ingest.record_file(r, cand("brief.html"), "s1")
        self.assertEqual(len(r["entries"]), 1)
        self.assertEqual(r["entries"][0]["type"], "artifact")

    def test_publish_without_source(self):
        r = reg()
        e = ingest.record_published(r, "https://claude.ai/artifact/x1", None, "T", "s1")
        self.assertEqual(e["type"], "artifact")
        self.assertIsNone(e["path"])
        self.assertIsNone(e["source_type"])

    def test_republish_same_url_is_change(self):
        r = reg()
        e = ingest.record_published(r, "https://claude.ai/artifact/x1", None, None, "s1")
        e.update(status="artifact", pending=None, noted_sessions=["s1"])
        e = ingest.record_published(r, "https://claude.ai/artifact/x1", None, None, "s2")
        self.assertEqual(len(r["entries"]), 1)
        self.assertEqual(e["pending"]["kind"], "changed")

    def test_server_dedup_by_cwd_and_command(self):
        r = reg()
        s = {"command": "npm run dev", "cwd": "app", "port": 5173}
        ingest.record_server(r, s, "s1")
        e = ingest.record_server(r, dict(s, port=None), "s1")
        self.assertEqual(len(r["entries"]), 1)
        self.assertEqual(e["type"], "server")
        self.assertEqual(e["server"]["port"], 5173)
        ingest.record_server(r, {"command": "npm run dev", "cwd": "web", "port": None}, "s1")
        self.assertEqual(len(r["entries"]), 2)

    def test_file_inside_group_touches_group(self):
        r = reg()
        files = [f"levels/{i}.html" for i in range(6)]
        g = ingest.record_file(r, cand("levels/", files=files), "s1")
        g.update(status="artifact", pending=None, noted_sessions=["s1"])
        e = ingest.record_file(r, cand("levels/3.html"), "s2")
        self.assertIs(e, g)
        self.assertEqual(e["pending"]["kind"], "changed")
        e2 = ingest.record_file(r, cand("levels/new.html"), "s2")
        self.assertIs(e2, g)
        self.assertIn("levels/new.html", g["files"])
        self.assertEqual(len(r["entries"]), 1)

    def test_find_entry(self):
        r = reg()
        ingest.record_file(r, cand("a.html"), "s1")
        self.assertIsNotNone(ingest.find_entry(r, path="a.html"))
        self.assertIsNone(ingest.find_entry(r, path="b.html"))
        self.assertIsNone(ingest.find_entry(r, url="https://claude.ai/artifact/zz"))


if __name__ == "__main__":
    unittest.main()
