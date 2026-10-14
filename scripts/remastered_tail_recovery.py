"""Recover only explicitly terminated UTF-8 fields; never complete source text."""
import re
from pathlib import Path

BAD_CONTROLS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

def recover_tail(row, message_key, root: Path, cache):
    if row['path'] not in cache:
        cache[row['path']] = (root / row['path']).read_bytes().split(b'\n')
    raw = cache[row['path']][row['line'] - 1].rstrip(b'\r')
    fields = raw.split(b'::')
    if len(fields) < 4 or fields[1] != message_key.encode('utf-8'):
        return None
    try:
        text = fields[2].decode('utf-8')
    except UnicodeDecodeError:
        return None
    if '\ufffd' in text or BAD_CONTROLS.search(text):
        return None
    # All recovered cases currently have an intact parsed text field. Reject
    # differences rather than silently changing a passage during alignment.
    if text != row['text']:
        return None
    return {'path': row['path'], 'line': row['line'], 'key': message_key,
            'text': text, 'trailerHex': b'::'.join(fields[3:]).hex()}

def page_tail_recovery(page, root: Path, cache):
    recovered = []
    for entry in page['entries']:
        for language in ['ja', 'en']:
            row = entry[language]
            if not row:
                return None
            if row['integrity'] == 'intact':
                continue
            evidence = recover_tail(row, entry['key'], root, cache)
            if evidence is None:
                return None
            recovered.append({'language': language, **evidence})
    return recovered
