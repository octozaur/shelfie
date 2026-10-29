import unittest

from shelfie import formats


class TypeForPathTest(unittest.TestCase):
    def test_type_for_path(self):
        self.assertEqual(formats.type_for_path("a/B.HTML"), "html")
        self.assertEqual(formats.type_for_path("x.markdown"), "md")
        self.assertEqual(formats.type_for_path("deck.key"), "slides")
        self.assertEqual(formats.type_for_path("t.tsv"), "sheet")
        self.assertEqual(formats.type_for_path("i.webp"), "image")
        self.assertIsNone(formats.type_for_path("x.py"))

    def test_all_in_table_order(self):
        self.assertEqual(formats.ALL, ["artifact", "html", "pdf", "md", "doc",
                                       "slides", "sheet", "server", "image"])
        self.assertEqual(formats.TYPES["server"]["badge"], "SERVER")
        self.assertEqual(formats.TYPES["artifact"]["color"], "#d97757")


if __name__ == "__main__":
    unittest.main()
