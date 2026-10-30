"""Verify reversible editorial changes and current patch/browser agreement."""
from pathlib import Path
import copy
import hashlib
import json
import re
import tempfile
import unittest

import editorial_release as editorial
import reader_release as release
from patch_tools.reader_projection import project_script
from patch_tools.xp3 import read, write

SITE = Path(__file__).resolve().parents[1]
DATA = SITE / 'public/data/script'
SETTINGS = {'singleRoute': False, 'playVitaOp': False, 'kag.isHd': False,
            'sf.rinGermanChant': False, 'sf.playUnmatchedVoices': False,
            "sf['g桜クリア']": True, 'sf.gセイバークリア': True, 'sf.g凛クリア': True}
for name in ['士郎', '慎二', 'セイバー', '凛', 'キャスター', '桜', 'ハサン', '臓硯']:
    SETTINGS[f"sf.voiceSetting['{name}'][1]"] = True


def without_english(value):
    if isinstance(value, dict):
        return {key: without_english(child) for key, child in value.items() if key != 'en'}
    if isinstance(value, list): return [without_english(child) for child in value]
    return value


class EditorialReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = editorial.data()
        cls.index = json.loads((DATA / 'index.json').read_text())
        cls.payloads = {meta['id']: json.loads((DATA / f"{meta['id']}.json").read_text())
                        for meta in cls.index['scripts']}
        cls.archive_path = SITE / 'public/downloads/patch_lang_english.xp3'
        cls.current = read(cls.archive_path)
        cls.previous = editorial.apply_native(cls.current, restore=True)
        cls.projections = {}

    def test_historical_overlay_is_immutable(self):
        self.assertEqual(hashlib.sha256(release.BINDINGS.read_bytes()).hexdigest(),
                         'aae193ea2a085c1a0c8555f0b205756b3ba7ce70f6bf64816ef8cfa788adef69')

    def test_current_and_reconstructed_archive_hashes(self):
        self.assertEqual(hashlib.sha256(self.archive_path.read_bytes()).hexdigest(), self.document['patch_sha256'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'patch.xp3'
            write(path, self.previous)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), editorial.BASE_PATCH_SHA256)
            write(path, editorial.apply_native(self.previous))
            self.assertEqual(path.read_bytes(), self.archive_path.read_bytes())

    def test_native_exact_delta_and_idempotence(self):
        self.assertEqual(editorial.apply_native(self.current), self.current)
        self.assertEqual(editorial.apply_native(self.previous, restore=True), self.previous)
        self.assertEqual(editorial.apply_native(self.previous), self.current)
        self.assertEqual(set(self.previous), set(self.current))
        allowed = {record['entry'] for record in self.document['native_bindings']}
        changed = {name for name in self.current if self.current[name] != self.previous[name]}
        self.assertEqual(changed, allowed)
        for name in self.current:
            if not name.endswith('.ks'): self.assertEqual(self.current[name], self.previous[name])
            else:
                _, old = editorial.native_pages(self.previous[name].decode('utf-16'))
                _, new = editorial.native_pages(self.current[name].decode('utf-16'))
                self.assertEqual([p['ref'] for p in old], [p['ref'] for p in new], name)

    def test_stale_native_page_fails_without_mutating_input(self):
        record = self.document['native_bindings'][0]
        files = dict(self.previous)
        payload = files[record['entry']]
        text = payload.decode('utf-16')
        lines, pages = editorial.native_pages(text)
        page = pages[record['ordinal']]
        lines[page['start'] + 1:page['start'] + 1] = ['STALE\r\n']
        files[record['entry']] = ''.join(lines).encode('utf-16')
        snapshot = dict(files)
        with self.assertRaisesRegex(ValueError, 'Stale native binding'):
            editorial.apply_native(files)
        self.assertEqual(files, snapshot)

    def test_current_browser_fields_are_exact_and_other_fields_preserved(self):
        allowed_japanese = {('0556', 'page70', 'original'), ('0607', 'page24', 'original')}
        seen_japanese = set()
        for record in editorial.records():
            page = editorial._page(self.payloads[record['script_id']]['pages'], record)
            names = set(record['before']) | set(record['after'])
            self.assertEqual(editorial._fields(page, names), record['after'])
            expected_before = copy.deepcopy(record['before'])
            if record.get('creates_edition_variants'):
                self.assertIs(record['creates_edition_variants'], True)
                self.assertEqual((record['script_id'], record['ref']), ('0607', 'page24'))
                self.assertNotIn('editions', expected_before)
                self.assertEqual(set(record['after']['editions']), {'original', 'all-ages'})
                expected_before['editions'] = {
                    edition: {field: copy.deepcopy(expected_before[field]) for field in ('en', 'ja', 'jaRuby')}
                    for edition in ('original', 'all-ages')
                }
            for correction in record.get('japanese_corrections', []):
                identity = (record['script_id'], record['ref'], correction['edition'])
                self.assertIn(identity, allowed_japanese)
                self.assertNotIn(identity, seen_japanese)
                seen_japanese.add(identity)
                self.assertEqual(set(correction['before']), {'ja', 'jaRuby'})
                self.assertEqual(set(correction['after']), {'ja', 'jaRuby'})
                witness = correction['source_witness']
                self.assertIsInstance(witness['path'], str)
                self.assertTrue(witness['path'].strip())
                self.assertRegex(witness['sha256'], r'^[0-9a-f]{64}$')
                self.assertEqual(witness['ref'], record['ref'])
                self.assertTrue(correction['reason'].strip())
                variant = expected_before['editions'][correction['edition']]
                for field in ('ja', 'jaRuby'):
                    self.assertEqual(variant[field], correction['before'][field])
                    self.assertIsInstance(correction['after'][field], str)
                    self.assertTrue(correction['after'][field].strip())
                    variant[field] = correction['after'][field]
            self.assertEqual(without_english(expected_before), without_english(record['after']),
                             (record['script'], record['ref'], 'Undocumented non-English binding fields changed'))
        self.assertEqual(seen_japanese, allowed_japanese)
        for payload in self.payloads.values():
            pages = copy.deepcopy(payload['pages'])
            self.assertEqual(editorial.apply(payload['script'], pages), 0)
            editorial.apply(payload['script'], pages, restore=True)
            self.assertEqual(editorial.apply(payload['script'], pages, restore=True), 0)
            editorial.apply(payload['script'], pages)
            self.assertEqual(pages, payload['pages'])
            release.apply(payload['script'], pages, restore=True)
            self.assertEqual(release.apply(payload['script'], pages, restore=True), 0)
            release.apply(payload['script'], pages)
            self.assertEqual(pages, payload['pages'])
            self.assertEqual(release.apply(payload['script'], pages), 0)

    def test_stale_editorial_page_fails_atomically(self):
        record = next(record for record in editorial.records() if record['before'] != record['after'])
        pages = copy.deepcopy(self.payloads[record['script_id']]['pages'])
        page = editorial._page(pages, record)
        field = next(iter(set(record['before']) | set(record['after'])))
        page[field] = 'STALE'
        snapshot = copy.deepcopy(pages)
        with self.assertRaisesRegex(ValueError, 'Stale (?:editorial|release) binding'):
            release.apply(record['script'], pages)
        self.assertEqual(pages, snapshot)

    def test_current_native_bindings_match_browser(self):
        checked = 0
        for record in editorial.records():
            page = editorial._page(self.payloads[record['script_id']]['pages'], record)
            for binding in record.get('native_bindings', []):
                edition = binding['edition']; parts = []
                for native in binding['contributors']:
                    key = (native['entry'], edition)
                    if key not in self.projections:
                        text = self.current[native['entry']].decode('utf-16')
                        effects = {name: f'⟦UNRENDERED:{name}⟧' for name in ['block', 'wacky', 'aero', 'margos', 'keraino']}
                        for body in re.findall(r'\[(block[^\]]*)\]', text):
                            length = re.search(r'len=(\d+)', body)
                            if length: effects[body] = '■' * int(length[1])
                        self.projections[key] = project_script(text, edition,
                            conditions={**SETTINGS, "sf['gレアルタ']": edition == 'all-ages'}, effects=effects)
                    native_page = self.projections[key][native['ordinal']]
                    self.assertEqual(native_page['ref'], native['native_ref'])
                    if native_page['en']: parts.append(native_page['en'])
                expected = '\n\n'.join(parts)
                actual = page.get('editions', {}).get(edition, page)['en']
                self.assertNotIn('⟦UNRENDERED:', expected)
                comparison = binding.get('comparison', 'exact')
                self.assertIn(comparison, ('exact', 'words'))
                if comparison == 'words':
                    self.assertEqual(re.findall(r'\w+', actual), re.findall(r'\w+', expected),
                                     (record['script'], record['ref'], edition))
                else:
                    self.assertEqual(actual, expected, (record['script'], record['ref'], edition))
                checked += 1
        self.assertGreater(checked, 0)

    def test_release_metadata_and_passage_ids(self):
        self.assertEqual(self.index['version'], editorial.VERSION)
        self.assertEqual(self.index['patchSha256'], self.document['patch_sha256'])
        self.assertEqual(self.index['scriptCount'], 729)
        self.assertEqual(self.index['pageCount'], 27530)
        for payload in self.payloads.values():
            before = [(page['ref'], page.get('availableEditions')) for page in payload['pages']]
            restored = copy.deepcopy(payload['pages'])
            editorial.apply(payload['script'], restored, restore=True)
            self.assertEqual([(page['ref'], page.get('availableEditions')) for page in restored], before)


if __name__ == '__main__':
    unittest.main()
