"""Project authored REMASTERED verdicts; never infer judgments or dossier claims."""
import json
from collections import defaultdict
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parents[1]
AUDIT = SITE.parent / 'audit/remastered_v1'
sys.path.insert(0, str(AUDIT))
from audit_io import verify_sources, check_saved_anchors

def read(path):
    return json.loads(path.read_text())

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')

def build():
    ledger = read(AUDIT / 'progress.json')
    verify_sources(ledger, full=True)
    check_saved_anchors(ledger)
    assert len({x['unit_id'] for x in ledger['coverage']}) == ledger['total_units']
    mirror = read(SITE / 'public/data/audit/dossiers.json')
    ordered_ids = [d['id'] for g in mirror['groups'] for d in g['dossiers']]
    assert len(ordered_ids) == len(set(ordered_ids))
    assert set(ordered_ids) == set(ledger['categories']), 'Category IDs must match mirror moon'
    public = SITE / 'public/data/audit/remastered'
    comparisons = SITE / 'public/data/comparisons/remastered'
    reader_index = read(SITE / 'public/data/script/index.json')
    labels = {d['id']: d['title'] for g in mirror['groups'] for d in g['dossiers']}
    public_notes = read(SITE / 'scripts/data/remastered-public-notes.json')
    classes = {
        'materially-different': 'wrong_meaning', 'logical-relation': 'wrong_logic',
        'actor-experiencer': 'wrong_subject', 'omission': 'omission',
        'unsupported-content': 'unsupported_addition', 'vagueness-euphemism': 'weakened_meaning',
        'inference-as-fact': 'unsupported_certainty', 'time-completion-duration': 'wrong_time_or_aspect',
        'grammar': 'grammar', 'word-choice': 'wrong_word',
        'japanese-shaped-idiom': 'unidiomatic_english', 'written-presentation': 'unclear_wording',
        'punctuation-typography': 'punctuation', 'name-address': 'name_or_address',
        'register-character-voice': 'changed_voice', 'jokes-wordplay': 'lost_wordplay',
    }
    destinations = defaultdict(list)
    for meta in reader_index['scripts']:
        payload = read(comparisons / f'{meta["id"]}.json')
        for ref, row in payload['rows'].items():
            if row['status'] == 'exact_japanese_text':
                destinations[row['sourceUnit']].append((meta['id'], ref, row['text']))

    def projection(item):
        note = public_notes.get(item['id'], {})
        category = note.get('category') or next((classes[c] for c in item['categories'] if c in classes), 'character_or_story_detail')
        anchors = item['anchors']
        # The first anchor is the asserted defect. Later anchors may be successful
        # context, so they must never automatically acquire red highlights.
        first = anchors[0]
        candidates = destinations.get(first['unit_id'], [])
        matching = [x for x in candidates if first['en']['quote'] in x[2]]
        target = matching[0] if len(matching) == 1 else None
        contexts = []
        for a in anchors:
            options = destinations.get(a['unit_id'], [])
            location = options[0] if len(options) == 1 else None
            contexts.append({'ref': a['unit_id'], 'japanese': a['ja']['quote'],
                             'english': a['en']['quote'],
                             'scriptId': location[0] if location else None,
                             'page': location[1] if location else None})
        return {'id': item['id'], 'description': note.get('description', item['description']),
                'sourceReading': note.get('sourceReading', item['source_reading']),
                'category': category,
                # These are the editor's authored descriptions, not the internal
                # verdict/defense dialogue. Publication edits can expand them.
                'explanation': note.get('explanation', item['description']),
                'severity': item['severity'],
                'categories': list(dict.fromkeys(item['categories'])), 'contexts': contexts,
                'scriptId': target[0] if target else None,
                'page': target[1] if target else None}

    findings = [projection(f) for f in ledger['findings']]
    counterexamples = [projection(c) for c in ledger['counterexamples']]
    finding_by_id = {f['id']: f for f in findings}
    counterexample_by_id = {c['id']: c for c in counterexamples}
    authored = {}
    for path in (AUDIT / 'dossier_writeups').glob('*.json'):
        doc = read(path)
        cid = doc['id']
        assert doc['schema'] == 'fsn-remastered-authored-dossier/1'
        assert doc['status'] == 'editorially_complete'
        assert path.stem == cid and cid in ordered_ids and cid not in authored
        assert doc['title'] == labels[cid]
        for field in ('claim', 'sourcePattern', 'englishEffect', 'limits'):
            assert doc[field].strip(), f'Missing authored {field}: {cid}'
        for field, records in (('exampleFindingIds', finding_by_id),
                               ('counterexampleIds', counterexample_by_id)):
            ids = doc[field]
            assert len(ids) == len(set(ids))
            for fid in ids:
                assert fid in records and cid in records[fid]['categories'], (cid, fid)
        assert doc['exampleFindingIds'], f'No cited evidence: {cid}'
        authored[cid] = doc
    by_script = defaultdict(list)
    for record, source in zip(findings, ledger['findings']):
        if record['scriptId'] is None:
            continue
        first = source['anchors'][0]
        by_script[record['scriptId']].append({
            'id': source['id'], 'ref': record['page'], 'category': record['category'],
            'status': 'confirmed', 'highlight': first['en']['quote'],
            'evidenceJa': first['ja']['quote'], 'governingReading': record['sourceReading'],
            'explanation': record['explanation'], 'dossiers': record['categories']})
    for meta in reader_index['scripts']:
        items = by_script[meta['id']]
        write(public / 'findings' / f'{meta["id"]}.json', {
            'schema': 'fsn-remastered-editorial-errors/1', 'scriptId': meta['id'],
            'findingCount': len(items), 'findings': items})
    write(public / 'findings/index.json', {
        'schema': 'fsn-remastered-editorial-error-index/1', 'totalFindings': len(findings),
        'mappedFindings': sum(len(x) for x in by_script.values()),
        'unmappedFindings': sum(f['scriptId'] is None for f in findings),
        'dossierLabels': labels,
        'routes': [{'scriptId': m['id'], 'findingCount': len(by_script[m['id']])} for m in reader_index['scripts']]})
    groups = []
    for group in mirror['groups']:
        categories = []
        for dossier in group['dossiers']:
            cid = dossier['id']
            selected = [f for f in findings if cid in f['categories']]
            limits = [c for c in counterexamples if cid in c['categories']]
            doc = authored.get(cid)
            assert not doc or doc['group'] == group['id'], f'Wrong dossier group: {cid}'
            manuscript = None if not doc else {
                **{key: doc[key] for key in ('claim', 'sourcePattern', 'englishEffect', 'limits')},
                'diagnostic': f'{len(selected):,} findings in this category; '
                              f'{len(doc["exampleFindingIds"])} cited passages.',
                'examples': [finding_by_id[fid] for fid in doc['exampleFindingIds']],
                'counterexamples': [counterexample_by_id[fid] for fid in doc['counterexampleIds']],
            }
            write(public / 'categories' / f'{cid}.json', {
                'schema': 'fsn-remastered-audit-category/1', 'id': cid,
                'dossier': manuscript, 'findings': selected, 'counterexamples': limits})
            categories.append({'id': cid, 'title': dossier['title'],
                               'confirmedCount': len(selected), 'counterexampleCount': len(limits),
                               'authored': bool(doc),
                               'exampleCount': len(doc['exampleFindingIds']) if doc else 0,
                               'citedCounterexampleCount': len(doc['counterexampleIds']) if doc else 0})
        groups.append({'id': group['id'], 'label': group['label'], 'dossiers': categories})
    write(public / 'index.json', {
        'schema': 'fsn-remastered-audit/1',
        'status': 'completed_corpus' if len(authored) == len(ordered_ids) else 'corpus_reviewed_dossiers_in_preparation',
        'authoredDossierCount': len(authored),
        'citedPassageCount': sum(len(d['exampleFindingIds']) for d in authored.values()),
        'uniqueCitedFindingCount': len({fid for d in authored.values() for fid in d['exampleFindingIds']}),
        'uniqueCitedCounterexampleCount': len({cid for d in authored.values() for cid in d['counterexampleIds']}),
        'reviewedPageCount': len(ledger['coverage']), 'totalPageCount': ledger['total_units'],
        'corpusConfirmedFindingCount': len(findings),
        'affectedPageCount': len({a['unit_id'] for f in ledger['findings'] for a in f['anchors']}),
        'withheldBorderlineCount': len(ledger['unresolved']),
        'counterexampleCount': len(counterexamples),
        'heldPageCount': sum(c['integrity_hold'] for c in ledger['coverage']),
        'dossierCount': len(ordered_ids), 'groups': groups})
    print(json.dumps({'findings': len(findings), 'readerHighlights': sum(len(x) for x in by_script.values()),
                      'categories': len(ordered_ids), 'authoredDossiers': len(authored),
                      'dossiers': 'complete' if len(authored) == len(ordered_ids) else 'in preparation'}))

if __name__ == '__main__':
    build()
