import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('spacing', Path(__file__).with_name('repair-empty-branch-spacing.py'))
spacing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spacing)

BRANCH = '@if exp="sf.gtext==\'realta\'"\r\n  \r\n@else\r\n  \r\n@endif\r\n'


class SpacingTests(unittest.TestCase):
    def test_reported_sentence(self):
        before = '  I wrench\r\n' + BRANCH + "  open the sliding door and rush into Saber's room.\r\n"
        after, changes = spacing.repair(before)
        for realta in (True, False):
            active = True
            rendered = ''
            for line in after.splitlines():
                if line.startswith('@if'): active = realta
                elif line == '@else': active = not realta
                elif line == '@endif': active = True
                elif active: rendered += line
            self.assertEqual(rendered.strip(), "I wrench open the sliding door and rush into Saber's room.")
        self.assertEqual(len(changes), 1)
        self.assertEqual(spacing.repair(after)[0], after)

    def test_breaks_and_real_branches_unchanged(self):
        source = '  First.[lr]\r\n' + BRANCH + '  Second.[lr]\r\n'
        after, _ = spacing.repair(source)
        self.assertTrue(after.endswith('  Second.[lr]\r\n'))
        for source in [BRANCH.replace('  \r\n@else', '  Actual text.\r\n@else'),
                       BRANCH.replace('sf.gtext', 'some.other.flag')]:
            self.assertEqual(spacing.repair(source)[0], source)


if __name__ == '__main__':
    unittest.main()
