import unittest

from reader_projection import ProjectionError, project_script


class ProjectionTests(unittest.TestCase):
    def pages(self, text, edition='original', **kwargs):
        return project_script(text, edition, **kwargs)

    def test_cross_page_conditions_and_duplicate_labels(self):
        source = '''@if exp="sf.gtext=='classic'"
*page1|
  Original.
*page1|
  Continued.
@else
  All ages.
@endif
'''
        original = self.pages(source)
        ages = self.pages(source, 'all-ages')
        self.assertEqual([p['en'] for p in original], ['Original.', 'Continued.'])
        self.assertEqual([p['en'] for p in ages], ['', 'All ages.'])
        self.assertEqual([p['ordinal'] for p in original], [0, 1])

    def test_elsif_and_ignore(self):
        source = '''*page0|
@if exp="sf.gtext=='mixed'"
  Wrong mixed.
@elsif exp="sf.gtext=='classic'"
  Original.
@else
  All ages.
@endif
@ignore exp="sf.ghentai"
  Extra.
@endignore
'''
        self.assertEqual(self.pages(source)[0]['en'], 'Original.')
        self.assertEqual(self.pages(source, 'all-ages')[0]['en'], 'All ages. Extra.')

    def test_unknown_text_condition_fails_but_short_circuit_is_safe(self):
        source = '''*page0|
@if exp="sf.gtext=='classic'&&unknown"
  Maybe.
@endif
'''
        with self.assertRaisesRegex(ProjectionError, 'Unknown text condition'):
            self.pages(source)
        self.assertEqual(self.pages(source, 'all-ages')[0]['en'], '')
        self.assertEqual(self.pages(source, conditions={'unknown': True})[0]['en'], 'Maybe.')

    def test_unknown_graphics_only_condition(self):
        source = '*page0|\n@if exp="unknown"\n@fadein file=black\n@endif\n  Text.\n'
        self.assertEqual(self.pages(source)[0]['en'], 'Text.')

    def test_physical_continuations_vs_native_breaks(self):
        source = '*page0|\n  I wash my\n  face.[lr]\n@r\n  The next paragraph.\n@pgnl\n  Continued screen.\n@pg\n'
        page = self.pages(source)[0]
        self.assertEqual(page['en'], 'I wash my face.\n\nThe next paragraph.\n\nContinued screen.')
        self.assertEqual(page['display_units'], ['I wash my face.\n\nThe next paragraph.', 'Continued screen.'])

    def test_text_commands_nested_tags_and_doublecolumn(self):
        source = '*page0|\n@align anchor="center" text="[line2]A[font italic=true]word[font italic=false]."\n@r\n@doublecolumn upper="“First.”" lower="“Second.”"\n'
        self.assertEqual(self.pages(source)[0]['en'], '——A*word*.\n\n“First.”\n\n“Second.”')

    def test_italic_survives_labels_and_screen_clear(self):
        source = '*page0|\n[font italic=true]First.\n@pgnl\nSecond.\n*page1|\nThird.[font italic=false]\n'
        pages = self.pages(source)
        self.assertEqual(pages[0]['en'], '*First.*\n\n*Second.*')
        self.assertEqual(pages[1]['en'], '*Third.*')

    def test_effects_require_explicit_mapping(self):
        source = '*page0|\n“[wacky len=12]!”\n'
        with self.assertRaisesRegex(ProjectionError, 'explicit reader rendering'):
            self.pages(source)
        page = self.pages(source, effects={'wacky len=12': '————'})[0]
        self.assertEqual(page['en'], '“————!”')
        self.assertEqual(page['effects'], ['wacky len=12'])

    def test_comments_script_blocks_ruby_and_font_expression(self):
        source = '''/*
*page99|
Hidden
*/
@iscript
Hidden
@endscript
*page0|
@font face="Times,"+&font size=27
[ruby text=Reading]Base[heart][auml]
'''
        self.assertEqual(self.pages(source)[0]['en'], 'Base♥ä')

    def test_unknown_inline_commands_fail(self):
        with self.assertRaisesRegex(ProjectionError, 'Unknown inline text command'):
            self.pages('*page0|\nText[unrecognized].\n')

    def test_unclosed_condition_fails(self):
        with self.assertRaisesRegex(ProjectionError, 'Unclosed conditional'):
            self.pages('*page0|\n@if exp="true"\nText.\n')


if __name__ == '__main__':
    unittest.main()
