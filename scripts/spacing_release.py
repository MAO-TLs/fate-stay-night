"""Exact reversible whitespace-only layer over v1.3.1."""
from pathlib import Path
import hashlib,json,re
from functools import cache
from patch_tools.xp3 import read
SITE=Path(__file__).resolve().parents[1]
VERSION='1.3.2'
@cache
def data():
 return json.loads((SITE/'scripts/data/spacing-v1.3.2.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def apply_native(files,restore=False):
 result=dict(files)
 for record in data()['edits']:
  payload=result[record['entry']]
  expected,target=(record['after_sha256'],record['before_sha256']) if restore else (record['before_sha256'],record['after_sha256'])
  if sha(payload)==target:continue
  if sha(payload)!=expected:raise ValueError('Stale spacing binding: '+record['entry'])
  text=payload.decode('utf-16');edits=[];shift=0
  for c in record['changes']:
   offset=c['offset']+(shift if restore else 0)
   old,new=(c['after'],c['before']) if restore else (c['before'],c['after'])
   edits.append((offset,old,new));shift+=len(c['after'])-len(c['before'])
  for offset,old,new in reversed(edits):
   assert text[offset:offset+len(old)]==old
   text=text[:offset]+new+text[offset+len(old):]
  result[record['entry']]=text.encode('utf-16')
  assert sha(result[record['entry']])==target
 return result
def verify_release():
 archive=SITE/'public/downloads/patch_lang_english.xp3'
 manifest=json.loads(archive.with_suffix('.manifest.json').read_text())
 rp=SITE/'public/downloads/patch_display_verification.json';report=json.loads(rp.read_text())
 assert manifest['version']==report['version']==VERSION
 assert sha(archive.read_bytes())==manifest['output_sha256']==report['archive_sha256']==data()['candidate_sha256']
 assert archive.stat().st_size==manifest['output_bytes']
 assert sha(rp.read_bytes())==manifest['display_verification_sha256']
 assert sha((SITE/'scripts/data/spacing-v1.3.2.json').read_bytes())==manifest['spacing_bindings_sha256']==report['spacing_bindings_sha256']
 files=read(archive);previous=apply_native(files,restore=True)
 assert apply_native(previous)==files and apply_native(files)==files
 assert files.keys()==previous.keys() and len(files)==895
 for name,payload in files.items():
  if not name.endswith('.ks'):assert payload==previous[name];continue
  old,new=previous[name].decode('utf-16'),payload.decode('utf-16')
  assert re.sub(r'\s','',old)==re.sub(r'\s','',new)
  assert [l for l in old.splitlines() if l.startswith(('@','*'))]==[l for l in new.splitlines() if l.startswith(('@','*'))]
 assert sum(files[n]!=previous[n] for n in files)==manifest['changed_entries']==79
 return previous
