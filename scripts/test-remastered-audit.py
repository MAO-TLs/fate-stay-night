"""Validate publication counts, independent category membership and safe reader links."""
import json
import re
from pathlib import Path
import unittest

SITE = Path(__file__).resolve().parents[1]
AUDIT = SITE.parent / 'audit/remastered_v1'

def read(path):
    return json.loads(path.read_text())

class RemasteredAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = read(AUDIT / 'progress.json')
        cls.public = SITE / 'public/data/audit/remastered'
        cls.index = read(cls.public / 'index.json')
        cls.findings = {f['id']: f for f in cls.ledger['findings']}
        cls.counterexamples = {c['id']: c for c in cls.ledger['counterexamples']}
        cls.public_notes = read(SITE / 'scripts/data/remastered-public-notes.json')

    def test_counts_and_categories_come_from_this_audit(self):
        index = self.index
        self.assertEqual(index['reviewedPageCount'], self.ledger['total_units'])
        self.assertEqual(index['corpusConfirmedFindingCount'], len(self.findings))
        self.assertEqual(index['withheldBorderlineCount'], len(self.ledger['unresolved']))
        self.assertEqual(index['counterexampleCount'], len(self.counterexamples))
        mirror = read(SITE / 'public/data/audit/dossiers.json')
        expected = [(g['id'], g['label'], [(d['id'], d['title']) for d in g['dossiers']]) for g in mirror['groups']]
        actual = [(g['id'], g['label'], [(d['id'], d['title']) for d in g['dossiers']]) for g in index['groups']]
        self.assertEqual(actual, expected)
        all_ids = set()
        for group in index['groups']:
            for category in group['dossiers']:
                cid = category['id']
                doc = read(self.public / 'categories' / f'{cid}.json')
                fs = {f['id'] for f in doc['findings']}
                cs = {c['id'] for c in doc['counterexamples']}
                self.assertEqual(fs, {k for k, f in self.findings.items() if cid in f['categories']})
                self.assertEqual(cs, {k for k, c in self.counterexamples.items() if cid in c['categories']})
                self.assertEqual(category['confirmedCount'], len(fs))
                self.assertEqual(category['counterexampleCount'], len(cs))
                all_ids.update(fs)
                for record in doc['findings'] + doc['counterexamples']:
                    source = self.findings.get(record['id']) or self.counterexamples[record['id']]
                    self.assertEqual(record['description'], self.public_notes.get(record['id'], {}).get('description', source['description']))
                    self.assertEqual(record['sourceReading'], self.public_notes.get(record['id'], {}).get('sourceReading', source['source_reading']))
                    self.assertNotIn('judgment', record)
                    self.assertNotIn('strongestAlternative', record)
                    self.assertEqual(record['explanation'], self.public_notes.get(record['id'], {}).get('explanation', source['description']))
                    self.assertEqual(record['categories'], list(dict.fromkeys(source['categories'])))
                    self.assertEqual([(c['japanese'], c['english']) for c in record['contexts']],
                                     [(a['ja']['quote'], a['en']['quote']) for a in source['anchors']])
        self.assertEqual(all_ids, set(self.findings))

    def test_all_public_findings_exclude_internal_verdict_prose(self):
        checked = {}
        for path in (self.public / 'categories').glob('*.json'):
            for record in read(path)['findings']:
                checked[record['id']] = record
                self.assertNotIn('judgment', record)
                self.assertNotIn('strongestAlternative', record)
                self.assertNotRegex(record['explanation'], r'(?i)^\s*(confirmed|withheld|adjudicated)\b')
                self.assertNotRegex(record['explanation'], r'(?i)\bindependently (verified|reviewed|repeats)\b')
                self.assertNotRegex(record['sourceReading'], r'(?i)\bRM-[A-Z0-9-]+|\b(checkpoint|packet|recheck)\b')
        self.assertEqual(set(checked), set(self.findings))

    def test_authored_dossiers_use_current_confirmed_evidence_and_own_claims(self):
        docs = {d['id']: d for p in (AUDIT / 'dossier_writeups').glob('*.json') for d in [read(p)]}
        self.assertEqual(self.index['authoredDossierCount'], len(docs))
        cited, unique = 0, set()
        for group in self.index['groups']:
            for category in group['dossiers']:
                cid = category['id']
                payload = read(self.public / 'categories' / f'{cid}.json')
                self.assertEqual(category['authored'], cid in docs)
                if cid not in docs:
                    self.assertIsNone(payload['dossier'])
                    continue
                source, public = docs[cid], payload['dossier']
                self.assertEqual(source['group'], group['id'])
                self.assertEqual(source['title'], category['title'])
                for key in ('claim', 'sourcePattern', 'englishEffect', 'limits'):
                    self.assertEqual(public[key], source[key])
                    self.assertTrue(public[key].strip())
                self.assertEqual([f['id'] for f in public['examples']], source['exampleFindingIds'])
                self.assertEqual([c['id'] for c in public['counterexamples']], source['counterexampleIds'])
                self.assertEqual(category['exampleCount'], len(public['examples']))
                self.assertEqual(category['citedCounterexampleCount'], len(public['counterexamples']))
                self.assertEqual(len(set(source['exampleFindingIds'])), len(source['exampleFindingIds']))
                for f in public['examples']:
                    self.assertIn(f['id'], self.findings)
                    self.assertIn(cid, self.findings[f['id']]['categories'])
                for c in public['counterexamples']:
                    self.assertIn(c['id'], self.counterexamples)
                    self.assertIn(cid, self.counterexamples[c['id']]['categories'])
                cited += len(public['examples'])
                unique.update(source['exampleFindingIds'])
        self.assertEqual(self.index['citedPassageCount'], cited)
        self.assertEqual(self.index['uniqueCitedFindingCount'], len(unique))

    def test_every_red_marker_has_a_unique_intact_matching_page(self):
        reader = read(SITE / 'public/data/script/index.json')
        total = 0
        seen = set()
        for script in reader['scripts']:
            sid = script['id']
            comparison = read(SITE / 'public/data/comparisons/remastered' / f'{sid}.json')
            notes = read(self.public / 'findings' / f'{sid}.json')
            self.assertEqual(notes['scriptId'], sid)
            self.assertEqual(notes['findingCount'], len(notes['findings']))
            for record in notes['findings']:
                self.assertNotIn(record['id'], seen)
                seen.add(record['id'])
                source = self.findings[record['id']]['anchors'][0]
                row = comparison['rows'][record['ref']]
                self.assertEqual(row['status'], 'exact_japanese_text')
                self.assertEqual(row['sourceUnit'], source['unit_id'])
                self.assertEqual(record['highlight'], source['en']['quote'])
                self.assertIn(record['highlight'], row['text'])
                self.assertEqual(record['evidenceJa'], source['ja']['quote'])
                self.assertEqual(record['dossiers'], list(dict.fromkeys(self.findings[record['id']]['categories'])))
                expected = self.public_notes.get(record['id'], {}).get('explanation', self.findings[record['id']]['description'])
                self.assertEqual(record['explanation'], expected)
                self.assertEqual(record['governingReading'], self.public_notes.get(record['id'], {}).get('sourceReading', self.findings[record['id']]['source_reading']))
                self.assertFalse(record['explanation'].startswith(('Confirmed:', 'Confirmed locally:', 'Withheld:')))
            total += len(notes['findings'])
        index = read(self.public / 'findings/index.json')
        self.assertEqual(total, index['mappedFindings'])
        self.assertEqual(total + index['unmappedFindings'], len(self.findings))

if __name__ == '__main__':
    unittest.main()
