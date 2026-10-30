"""Exact, reversible v1.3.1 changes layered over the frozen v1.3.0 release."""
from pathlib import Path
from functools import cache
import copy
import json
import re

SITE = Path(__file__).resolve().parents[1]
BINDINGS = SITE / 'scripts/data/reader-v1.3.1.json'
VERSION = '1.3.1'
BASE_PATCH_SHA256 = '6e31d6b3208e60654206a17b0a816bdc1807750bc14083a01ac6dca38cc7e242'


@cache
def data():
    result = json.loads(BINDINGS.read_text())
    if result['version'] != VERSION or result['base_patch_sha256'] != BASE_PATCH_SHA256:
        raise ValueError('Unexpected editorial release ancestry')
    if not re.fullmatch(r'[0-9a-f]{64}', result['patch_sha256']):
        raise ValueError('Invalid editorial patch digest')
    for field, key in [('bindings', lambda row: (row['script'], row['ref'], row.get('occurrence', 0))),
                       ('native_bindings', lambda row: (row['entry'], row['ordinal']))]:
        identities = [key(row) for row in result[field]]
        if len(identities) != len(set(identities)):
            raise ValueError(f'Duplicate editorial {field}')
    return result


def records():
    return data()['bindings']


def _page(pages, record):
    matches = [page for page in pages if page['ref'] == record['ref']]
    occurrence = record.get('occurrence', 0)
    if occurrence < 0 or occurrence >= len(matches):
        raise ValueError(f"Missing editorial passage: {record['script']}:{record['ref']}:{occurrence}")
    return matches[occurrence]


def _fields(page, names):
    return {key: copy.deepcopy(page[key]) for key in names if key in page}


def _replace(page, target, names):
    for key in names:
        if key in target: page[key] = copy.deepcopy(target[key])
        else: page.pop(key, None)


def apply(script, pages, *, restore=False):
    """Apply just the editorial browser layer, validating all pages before edits."""
    pending = []
    for record in records():
        if record['script'] != script: continue
        page = _page(pages, record)
        names = sorted(set(record['before']) | set(record['after']))
        current = _fields(page, names)
        expected, target = (record['after'], record['before']) if restore else (record['before'], record['after'])
        if current == target: continue
        if current != expected:
            raise ValueError(f"Stale editorial binding: {script}:{record['ref']}:{record.get('occurrence', 0)}")
        pending.append((page, target, names))
    for page, target, names in pending: _replace(page, target, names)
    return len(pending)


def undo_applied(script, pages):
    """Undo only recognized latest fields before historical validation.

    A historical manuscript page may match neither editorial state yet. Leave
    that page intact so the historical layer validates it before editorial apply.
    Unrecognized state never bypasses the subsequent strict forward validation.
    """
    for record in records():
        if record['script'] != script: continue
        page = _page(pages, record)
        names = sorted(set(record['before']) | set(record['after']))
        if _fields(page, names) == record['after']:
            _replace(page, record['before'], names)


def native_pages(text):
    """Locate native page occurrences without interpreting comments or TJS."""
    lines = text.splitlines(keepends=True)
    pages = []; comment = script = False
    for index, line in enumerate(lines):
        value = line.strip()
        if value.startswith('/*'): comment = True
        if comment:
            if '*/' in value: comment = False
            continue
        if value.startswith(';'): continue
        if re.match(r'@iscript\b', value): script = True
        if script:
            if re.match(r'@endscript\b', value): script = False
            continue
        match = re.match(r'^\*(page\d+)(?:\||\s*$)', line)
        if match:
            if pages: pages[-1]['end'] = index
            pages.append({'ref': match[1], 'start': index, 'end': len(lines)})
    if comment or script: raise ValueError('Unclosed native comment or TJS block')
    return lines, pages


def apply_native(files, *, restore=False):
    """Return a corrected copy; exact native page bindings fail closed on drift."""
    result = dict(files)
    for record in data()['native_bindings']:
        entry = record['entry']
        if entry not in result: raise ValueError(f'Missing native entry: {entry}')
        payload = result[entry]
        if not payload.startswith((b'\xff\xfe', b'\xfe\xff')):
            raise ValueError(f'Native entry is not BOM-marked UTF-16: {entry}')
        text = payload.decode('utf-16')
        lines, pages = native_pages(text)
        ordinal = record['ordinal']
        if ordinal < 0 or ordinal >= len(pages) or pages[ordinal]['ref'] != record['ref']:
            raise ValueError(f'Native page identity mismatch: {entry}:{ordinal}')
        page = pages[ordinal]
        current = ''.join(lines[page['start']:page['end']])
        expected, target = (record['after'], record['before']) if restore else (record['before'], record['after'])
        if current == target: continue
        if current != expected: raise ValueError(f'Stale native binding: {entry}:{ordinal}:{record["ref"]}')
        lines[page['start']:page['end']] = [target]
        updated = ''.join(lines)
        _, new_pages = native_pages(updated)
        if [p['ref'] for p in pages] != [p['ref'] for p in new_pages]:
            raise ValueError(f'Native page labels changed: {entry}')
        encoding = 'utf-16-le' if payload.startswith(b'\xff\xfe') else 'utf-16-be'
        result[entry] = payload[:2] + updated.encode(encoding)
    return result
