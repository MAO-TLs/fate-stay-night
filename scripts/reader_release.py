"""Apply frozen release corrections after the historical manuscript build.

Only explicitly reviewed fields change. A stale historical page fails closed;
reapplying the same version is idempotent. Script IDs and passage refs stay put.
"""
from pathlib import Path
import copy
import hashlib
import json
from functools import cache

SITE = Path(__file__).resolve().parents[1]
BINDINGS = SITE / 'scripts/data/reader-v1.3.0.json'
VERSION = '1.3.0'
PATCH_SHA256 = '6e31d6b3208e60654206a17b0a816bdc1807750bc14083a01ac6dca38cc7e242'

@cache
def records():
    data = json.loads(BINDINGS.read_text())
    assert data['version'] == VERSION and data['patch_sha256'] == PATCH_SHA256
    return data['bindings']

def _page(pages, record):
    matches = [page for page in pages if page['ref'] == record['ref']]
    occurrence = record.get('occurrence', 0)
    if occurrence >= len(matches):
        raise ValueError(f"Missing release passage: {record['script']}:{record['ref']}:{occurrence}")
    return matches[occurrence]

def fields(page, names):
    return {key: copy.deepcopy(page[key]) for key in names if key in page}

def replace(page, values, names):
    for key in names:
        if key in values: page[key] = copy.deepcopy(values[key])
        else: page.pop(key, None)

def apply(script, pages, *, restore=False):
    changed = 0
    for record in records():
        if record['script'] != script: continue
        page = _page(pages, record)
        keys = sorted(set(record['before']) | set(record['after']))
        current = fields(page, keys)
        expected, target = (record['after'], record['before']) if restore else (record['before'], record['after'])
        if current == target: continue
        if current != expected:
            raise ValueError(f"Stale release binding: {script}:{record['ref']}:{record.get('occurrence',0)}")
        replace(page, target, keys)
        changed += 1
    return changed

def sync(*, check=False):
    folder = SITE / 'public/data/script'
    index = json.loads((folder/'index.json').read_text())
    outputs = {}; concordance=[]; changed=0
    for meta in index['scripts']:
        path = folder / f"{meta['id']}.json"
        payload = json.loads(path.read_text())
        changed += apply(meta['script'], payload['pages'])
        outputs[path] = json.dumps(payload,ensure_ascii=False,separators=(',',':'))
        concordance.extend({'scriptId':meta['id'],'script':meta['script'],'route':meta['route'],'title':meta['title'],
                            **{k:v for k,v in page.items() if k!='mirrorMoon'}} for page in payload['pages'])
    index.update(version=VERSION,patchSha256=PATCH_SHA256)
    outputs[folder/'index.json']=json.dumps(index,ensure_ascii=False,separators=(',',':'))
    outputs[folder/'concordance.json']=json.dumps(concordance,ensure_ascii=False,separators=(',',':'))
    if check:
        for path,content in outputs.items():
            if path.read_text()!=content: raise ValueError(f'Reader release is out of date: {path.name}')
    else:
        for path,content in outputs.items():
            if path.read_text()!=content: path.write_text(content)
    print(json.dumps({'version':VERSION,'changed_passages':changed,'bindings':len(records()),'check':check}))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true')
    sync(check=parser.parse_args().check)
