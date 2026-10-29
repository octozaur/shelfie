import unittest

from shelfie import ingest, notes


def reg_with(*paths, session="s1"):
    r = {"version": 1, "entries": []}
    for p in paths:
        ingest.record_file(r, {"path": p, "type": "html", "files": None}, session)
    return r


class PendingTest(unittest.TestCase):
    def test_pending_entries(self):
        r = reg_with("a.html", "b.html")
        r["entries"][1]["pending"] = None
        self.assertEqual([e["path"] for e in notes.pending_entries(r)], ["a.html"])


class ApplyNoteTest(unittest.TestCase):
    def test_new_artifact(self):
        r = reg_with("a.html")
        e = r["entries"][0]
        at = e["pending"]["at"]
        notes.apply_note(r, e["id"], True, "Title", "Desc.", None)
        self.assertEqual(e["status"], "artifact")
        self.assertEqual((e["title"], e["description"]), ("Title", "Desc."))
        self.assertEqual(e["changes"], [{"at": at, "note": "Created"}])
        self.assertIsNone(e["pending"])
        self.assertEqual(e["noted_sessions"], ["s1"])

    def test_new_with_change_line(self):
        r = reg_with("a.html")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], True, "T", "D", "First draft with charts")
        self.assertEqual([c["note"] for c in e["changes"]], ["Created", "First draft with charts"])

    def test_not_artifact_is_ignored(self):
        r = reg_with("README.md")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], False, None, None, None)
        self.assertEqual(e["status"], "ignored")
        self.assertIsNone(e["pending"])
        self.assertEqual(e["noted_sessions"], ["s1"])

    def test_changed_appends_and_keeps_title(self):
        r = reg_with("a.html")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], True, "T", "D", None)
        ingest.record_file(r, {"path": "a.html", "type": "html", "files": None}, "s2")
        notes.apply_note(r, e["id"], True, None, None, "Added Q4 numbers")
        self.assertEqual(e["changes"][-1]["note"], "Added Q4 numbers")
        self.assertEqual(e["title"], "T")
        self.assertEqual(e["noted_sessions"], ["s1", "s2"])

    def test_changed_without_line_says_updated(self):
        r = reg_with("a.html")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], True, "T", "D", None)
        ingest.record_file(r, {"path": "a.html", "type": "html", "files": None}, "s2")
        notes.apply_note(r, e["id"], True, None, "New desc", None)
        self.assertEqual(e["changes"][-1]["note"], "Updated")
        self.assertEqual(e["description"], "New desc")

    def test_note_without_pending_updates_text_only(self):
        r = reg_with("a.html")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], True, "T", "D", None)
        notes.apply_note(r, e["id"], True, "T2", None, None)
        self.assertEqual(e["title"], "T2")
        self.assertEqual(len(e["changes"]), 1)

    def test_unknown_id(self):
        with self.assertRaises(KeyError):
            notes.apply_note(reg_with(), "zzzzzz", True, None, None, None)


class SetStatusTest(unittest.TestCase):
    def test_restore_titled_item(self):
        r = reg_with("a.html")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], True, "T", "D", None)
        notes.set_status(r, e["id"], "ignored")
        self.assertEqual(e["status"], "ignored")
        notes.set_status(r, e["id"], "artifact")
        self.assertEqual(e["status"], "artifact")

    def test_restore_untitled_goes_pending(self):
        r = reg_with("README.md")
        e = r["entries"][0]
        notes.apply_note(r, e["id"], False, None, None, None)
        notes.set_status(r, e["id"], "artifact")
        self.assertEqual(e["status"], "pending")
        self.assertEqual(e["pending"]["kind"], "new")


class StopReasonTest(unittest.TestCase):
    def test_reason_lists_entries_and_usage(self):
        r = reg_with("a.html")
        ingest.record_server(r, {"command": "npm run dev", "cwd": ".", "port": 5173}, "s1")
        text = notes.stop_reason(notes.pending_entries(r))
        e1, e2 = r["entries"]
        self.assertIn(f"{e1['id']} · NEW · html · a.html", text)
        self.assertIn(f"{e2['id']} · NEW · server · npm run dev", text)
        self.assertIn(".shelfie/bin/shelfie note <id> --artifact yes|no", text)

    def test_reason_uses_given_command(self):
        r = reg_with("a.html")
        text = notes.stop_reason(notes.pending_entries(r), "'/p q/.shelfie/bin/shelfie'")
        self.assertIn("'/p q/.shelfie/bin/shelfie' note <id> --artifact yes|no", text)

    def test_stop_reason_truncates(self):
        r = reg_with(*[f"f{i}.html" for i in range(25)])
        text = notes.stop_reason(notes.pending_entries(r))
        self.assertIn("+15 more", text)
        self.assertLessEqual(len(text), 1500)


if __name__ == "__main__":
    unittest.main()
