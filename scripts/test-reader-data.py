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


if __name__ == "__main__":
    unittest.main()
