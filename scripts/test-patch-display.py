"""Verify current exact repairs while retaining immutable historical display evidence."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'patch_tools'))
from xp3 import read
from sweep_script import inspect
from repair_candidate import repair_files
import editorial_release as editorial

site=HERE.parent;archive=site/'public/downloads/patch_lang_english.xp3'
manifest=json.loads(archive.with_suffix('.manifest.json').read_text())
report_path=site/'public/downloads/patch_display_verification.json'
report=json.loads(report_path.read_text());delta=editorial.data()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())==manifest['output_sha256']==delta['patch_sha256']==report['archive_sha256']
assert archive.stat().st_size==manifest['output_bytes']
assert manifest['version']==report['version']==editorial.VERSION
assert manifest['runtime_tested'] is False and report['runtime_tested'] is False
assert manifest['browser']['version']==editorial.VERSION
assert sha(report_path.read_bytes())==manifest['display_verification_sha256']
assert sha(editorial.BINDINGS.read_bytes())==manifest['editorial_repair']['bindings_sha256']==report['current_delta']['delta_sha256']
files=read(archive);previous=editorial.apply_native(files,restore=True)
assert len(files)==manifest['entries']==895
scripts,pages,commands,issues=inspect(files)
assert not issues,issues
assert scripts==report['full_script_scan']['scripts_checked']==734
assert pages==report['full_script_scan']['page_labels_checked']==27918
assert sorted(commands)==report['full_script_scan']['command_names']
assert repair_files(files)==(files,[]),'Existing display cleanup regressed'
for name in files:
 if not name.endswith('.ks'):
  assert files[name]==previous[name],name
  continue
 old,new=previous[name].decode('utf-16'),files[name].decode('utf-16')
 assert re.findall(r'(?m)^[\t ]*@[^\r\n]+',old)==re.findall(r'(?m)^[\t ]*@[^\r\n]+',new),(name,'cue/action/control command changed')
 assert re.findall(r'^\*page\d+.*$',old,re.M)==re.findall(r'^\*page\d+.*$',new,re.M),(name,'labels changed')
for entry in manifest['editorial_repair']['changed_entries']:
 assert sha(previous[entry['entry']])==entry['before_sha256']
 assert sha(files[entry['entry']])==entry['after_sha256']
assert sum(files[n]!=previous[n] for n in files)==manifest['changed_entries']==40
# Voice-trigger regression anchors: the cue must precede its complete spoken unit.
for name,cue,prefix in [
 ('セイバールート三日目-16.ks','sav0316_ran_0200','“What…!?”'),
 ('凛ルート八日目-00.ks','rin0800_shi_0040','“Issei. Take off your jacket'),
 ('桜ルート九日目-37.ks','sak0937_zok_0060','“Still, it is something of a pity.'),
 ('凛ルート十四日目-18.ks','rin1418_cas_0040','If so, there is no question'),
 ('セイバールート十日目-07.ks','sav1007_rin_0330','“If you are going to decide'),
 ('セイバールート四日目-07.ks','sav0407_sav_0000','“…? My body is as you see it.'),
 ('桜ルート八日目-20.ks','sak0820_sak_0121','“I-I’m starting,”'),
 ('桜ルート十日目-26.ks','sak1026_rad_0180','That changed after she came to know you')]:
 assert '@say storage='+cue+'\r\n  '+prefix in files[name].decode('utf-16'),(name,cue)
# This report describes v1.3.0 only, not fresh v1.3.1 break-count parity.
history=report['inherited_verification'];path=site/history['report_path']
assert sha(path.read_bytes())==history['report_sha256']
old_report=json.loads(path.read_text());assert old_report['archive_sha256']==history['archive_sha256']==editorial.BASE_PATCH_SHA256
assert old_report['version']=='1.3.0'
parity=old_report['mirror_moon_display_parity']
assert parity['candidate_sha256']==editorial.BASE_PATCH_SHA256
assert parity['remaining_hold_rows']==0 and parity['previous_held_rows_resolved']==10
assert parity['profiles_skipped_unaligned']==0 and parity['unknown_condition_comparisons_unresolved']==0
assert parity['unknown_condition_edition_comparisons_enumerated']==110
assert parity['edition_rows_checked']==48408
assert parity['matching_edition_rows']+parity['raw_mirror_mismatch_rows']==parity['edition_rows_checked']
assert parity['raw_mirror_mismatch_rows']==len(parity['source_supported_divergences'])
assert parity['residuals_exactly_match_reviewed_source_divergences']
print('PASS: current archive, all734 scripts/27918 labels, unchanged cue/action commands, eight repaired cue boundaries, and separate historical display proof')
