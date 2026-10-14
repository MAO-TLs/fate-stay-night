"""Publish only exact Japanese-text alignments. No fuzzy/page-label fallback."""
from pathlib import Path
from collections import defaultdict, Counter
import importlib.util
import json
import re
import hashlib
from remastered_tail_recovery import page_tail_recovery

SITE = Path(__file__).resolve().parents[1]
AUDIT = SITE.parent / 'audit/remastered_v1'
spec = importlib.util.spec_from_file_location('remastered_prepare', AUDIT / 'prepare.py')
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)

def clean_japanese(text):
    text = prep.visible(text).replace('—', '')
    return re.sub(r'\s+', '', text)

def build():
    inventory = json.loads((AUDIT / 'inventory.json').read_text())
    for file in inventory['files']:
        if prep.sha(SITE.parent / file['path']) != file['sha256']:
            raise ValueError(f'Changed witness: {file["path"]}')
    out = SITE / 'public/data/comparisons/remastered'
    out.mkdir(parents=True, exist_ok=True)
    index = json.loads((SITE / 'public/data/script/index.json').read_text())
    counts = Counter()
    scripts = []
    raw_cache = {}
    recovery_report = {}
    for meta in index['scripts']:
        corpus = AUDIT / 'corpus' / (meta['script'] + '.json')
        reader = json.loads((SITE / 'public/data/script' / (meta['id'] + '.json')).read_text())
        candidates = defaultdict(list)
        if corpus.exists():
            rec = json.loads(corpus.read_text())
            for page in rec['pages']:
                jp = clean_japanese(page['ja'])
                if jp:
                    candidates[jp].append(page)
        rows = {}
        used = set()
        refs = Counter(row['ref'] for row in reader['pages']
                       if 'all-ages' in row.get('availableEditions', ['original', 'all-ages']))
        for row in reader['pages']:
            if 'all-ages' not in row.get('availableEditions', ['original', 'all-ages']):
                continue
            variant = row.get('editions', {}).get('all-ages', row)
            if refs[row['ref']] > 1:
                rows[row['ref']] = {'status': 'duplicate_reference_hold', 'text': None, 'sourceUnit': None}
                continue
            fp = clean_japanese(variant['ja'])
            matches = candidates.get(fp, []) if fp else []
            match = matches[0] if len(matches) == 1 else None
            status = 'unresolved_alignment'
            text = None
            if match:
                recovery = page_tail_recovery(match, SITE.parent, raw_cache) if match['integrity_hold'] else []
                if match['integrity_hold'] and recovery is None:
                    status = 'source_integrity_hold'
                elif match['conditional']:
                    status = 'conditional_alignment_hold'
                else:
                    status = 'exact_japanese_text'
                    text = prep.visible(match['en'])
                    used.add(match['unit_id'])
                    if recovery:
                        recovery_report[match['unit_id']] = recovery
            elif not fp:
                status = 'no_display_text'
            rows[row['ref']] = {'status': status, 'text': text,
                                'sourceUnit': match['unit_id'] if match else None,
                                **({'recoveredDelimitedTail': True} if status == 'exact_japanese_text' and recovery else {})}
        counts.update(row['status'] for row in rows.values())
        payload = {'schema': 'fsn-remastered-comparison/1', 'scriptId': meta['id'], 'rows': rows}
        prep.dump(out / f'{meta["id"]}.json', payload)
        scripts.append({'scriptId':meta['id'], 'script':meta['script'],
                        'aligned':len(used), 'candidate_source_pages':sum(len(x) for x in candidates.values())})
    prep.dump(out / 'index.json', {'schema':'fsn-remastered-comparison-index/1',
        'edition':'all-ages', 'witnessCommit':inventory['commit'],
        'provenanceLimit':inventory['provenance_limit'], 'alignment':'Unique exact Japanese visible-text match within the same scene; dash controls and whitespace normalized.',
        'counts':dict(counts), 'scripts':scripts})
    prep.dump(AUDIT / 'comparison-tail-recovery.json', {
        'method': 'Only complete UTF-8 text fields followed by an explicit :: closing separator; parsed text remains byte-equivalent. Trailers are excluded from matching, never from the frozen source.',
        'recovered_comparison_units': len(recovery_report),
        'units': [{'unit_id': uid, 'rows': rows} for uid, rows in sorted(recovery_report.items())]})
    print(json.dumps(dict(counts)))

if __name__ == '__main__':
    build()
