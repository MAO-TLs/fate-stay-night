"""Boundary tests: footer recovery must never guess a text-field ending."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from remastered_tail_recovery import recover_tail

class TailRecoveryTest(unittest.TestCase):
    def check_row(self, data, text, expected):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / 'row').write_bytes(data)
            row = {'path': 'row', 'line': 1, 'text': text}
            recovered = recover_tail(row, '$$$message_test$$$', root, {})
            self.assertEqual(recovered is not None, expected)
            if expected:
                self.assertEqual(recovered['text'], text)

    def test_invalid_footer_after_explicit_end_is_recoverable(self):
        self.check_row(b'42::$$$message_test$$$::A distant dream takes her.::\xa9>', 'A distant dream takes her.', True)

    def test_japanese_text_with_ascii_footer_is_recoverable(self):
        text = '「それじゃあね。」'
        self.check_row(('42::$$$message_test$$$::' + text + '::%').encode(), text, True)

    def test_invalid_bytes_inside_field_are_not_recoverable(self):
        self.check_row(b'42::$$$message_test$$$::A distant \xffdream.::>', 'A distant �dream.', False)

    def test_missing_end_is_not_inferred_from_a_period(self):
        self.check_row(b'42::$$$message_test$$$::A distant dream.', 'A distant dream.', False)

    def test_control_bytes_inside_text_are_not_footer(self):
        self.check_row(b'42::$$$message_test$$$::A dream.\x04::>', 'A dream.\x04', False)

    def test_mismatched_key_and_changed_parsed_text_are_rejected(self):
        self.check_row(b'42::$$$other$$$::Dream.::>', 'Dream.', False)
        self.check_row(b'42::$$$message_test$$$::Dream.::>', 'Dream', False)

if __name__ == '__main__':
    unittest.main()
