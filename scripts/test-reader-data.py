import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("reader_data", Path(__file__).with_name("build-reader-data.py"))
reader_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader_data)


class ReaderDataTests(unittest.TestCase):
    def test_review_sections_do_not_become_translation(self):
        source = Mock()
        source.read_text.return_value = (
            "# Manuscript\nIntroductory notes\n"
            "## page0\nActual prose.\n\n"
            "## Governing decisions\n- Internal note.\n"
            "### Root review\nMore notes.\n"
            "## page1\nNext passage.\n"
            "## Review notes\n- Another note.\n"
        )
        self.assertEqual(reader_data.english_pages(source),
                         [("page0", "Actual prose."), ("page1", "Next passage.")])

    def test_new_order_does_not_renumber_existing_links(self):
        published = [{"script":"base", "id":"0042"}, {"script":"restored", "id":"0043"}]
        self.assertEqual(reader_data.stable_ids(["epilogue", "restored", "base"], published),
                         {"base":"0042", "restored":"0043", "epilogue":"0044"})

    def test_shrinking_inventory_is_rejected(self):
        with self.assertRaises(RuntimeError):
            reader_data.stable_ids(["base"], [{"script":"base", "id":"0000"}, {"script":"restored", "id":"0001"}])

    def test_commented_labels_keep_active_text_and_glyphs(self):
        source = Mock()
        source.read_text.return_value = "*page71|\nBefore.\n;*page72|\nStill active.\n*page78|\nl[auml][szlig]t\n"
        self.assertEqual(reader_data.japanese_pages(source), [("page71", "Before.\nStill active."), ("page78", "läßt")])


if __name__ == "__main__":
    unittest.main()
