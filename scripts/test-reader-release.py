"""Check frozen browser updates, native prose, editions, and search consistency."""
from pathlib import Path
import copy
import hashlib
import json
import re
import unittest
import reader_release as release
import editorial_release as editorial
from patch_tools.reader_projection import project_script
from patch_tools.xp3 import read

SITE=Path(__file__).resolve().parents[1]
DATA=SITE/'public/data/script'
SETTINGS={'singleRoute':False,'playVitaOp':False,'kag.isHd':False,'sf.rinGermanChant':False,'sf.playUnmatchedVoices':False,
          "sf['g桜クリア']":True,'sf.gセイバークリア':True,'sf.g凛クリア':True}
for name in ['士郎','慎二','セイバー','凛','キャスター','桜','ハサン','臓硯']:SETTINGS[f"sf.voiceSetting['{name}'][1]"]=True

class ReaderReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((DATA/'index.json').read_text())
        cls.payloads={s['id']:json.loads((DATA/f"{s['id']}.json").read_text()) for s in cls.index['scripts']}
        archive=SITE/'public/downloads/patch_lang_english.xp3'
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==release.PATCH_SHA256
        cls.archive=editorial.apply_native(read(archive),restore=True);cls.projections={}
        cls.current_payloads=cls.payloads
        cls.payloads=copy.deepcopy(cls.current_payloads)
        for payload in cls.payloads.values():
            editorial.apply(payload['script'],payload['pages'],restore=True)
    def test_idempotent_and_exact_binding_fields(self):
        for data in self.current_payloads.values():
            clone=copy.deepcopy(data['pages'])
            self.assertEqual(release.apply(data['script'],clone),0)
            self.assertEqual(clone,data['pages'])
    def test_stale_input_fails_closed(self):
        record=release.records()[0]
        page={'ref':record['ref'],**copy.deepcopy(record['before'])}
        first=next(iter(record['before']));page[first]='Stale text'
        with self.assertRaisesRegex(ValueError,'Stale release binding'):
            release.apply_historical(record['script'],[page])
    def test_backward_and_forward_projection_preserves_other_fields(self):
        for data in self.current_payloads.values():
            clone=copy.deepcopy(data['pages'])
            release.apply(data['script'],clone,restore=True)
            release.apply(data['script'],clone)
            self.assertEqual(clone,data['pages'])
    def test_native_words_and_edition_paths(self):
        for record in release.records():
            page=release._page(self.payloads[record['script_id']]['pages'],record)
            for bound in record['native_bindings']:
                ed=bound['edition'];parts=[]
                for native in bound['contributors']:
                    k=(native['entry'],ed)
                    if k not in self.projections:
                        text=self.archive[native['entry']].decode('utf-16')
                        effects={x:f'⟦UNRENDERED:{x}⟧' for x in ['block','wacky','aero','margos','keraino']}
                        for body in re.findall(r'\[(block[^\]]*)\]',text):
                            length=re.search(r'len=(\d+)',body)
                            if length:effects[body]='■'*int(length[1])
                        self.projections[k]=project_script(text,ed,conditions={**SETTINGS,"sf['gレアルタ']":ed=='all-ages'},effects=effects)
                    part=self.projections[k][native['ordinal']]['en']
                    if part:parts.append(part)
                expected='\n\n'.join(parts)
                self.assertNotIn('⟦UNRENDERED:',expected)
                for correction in record.get('reader_corrections',[]):
                    if correction['edition']==ed:
                        self.assertEqual(expected.count(correction['before']),1)
                        expected=expected.replace(correction['before'],correction['after'])
                self.assertEqual(page.get('editions',{}).get(ed,page)['en'],expected,(record['script'],record['ref'],ed))
    def test_search_and_page_data_are_identical(self):
        expected=[]
        for meta in self.index['scripts']:
            for page in self.current_payloads[meta['id']]['pages']:
                expected.append({'scriptId':meta['id'],'script':meta['script'],'route':meta['route'],'title':meta['title'],
                                 **{k:v for k,v in page.items() if k!='mirrorMoon'}})
        self.assertEqual(json.loads((DATA/'concordance.json').read_text()),expected)
        self.assertEqual(self.index['scriptCount'],729)
        self.assertEqual(self.index['pageCount'],27530)
        self.assertEqual(self.index['version'],release.VERSION)
        self.assertEqual(self.index['patchSha256'],release.PATCH_SHA256)
    def test_japanese_counterparts_match_reviewed_editions(self):
        checked=0
        for record in release.records():
            page=release._page(self.payloads[record['script_id']]['pages'],record)
            for binding in record.get('japanese_counterparts',[]):
                variant=page['editions'][binding['edition']]
                for field,value in binding['after'].items():
                    self.assertEqual(variant[field],value)
                    if binding['edition']=='all-ages':self.assertEqual(page[field],value)
                self.assertEqual(hashlib.sha256(variant['jaRuby'].encode()).hexdigest(),binding['after_jaRuby_sha256'])
                checked+=1
        self.assertEqual(checked,184)
    def test_virtual_original_passage_has_no_shared_duplicate(self):
        pages={p['ref']:p for p in self.payloads['0574']['pages']}
        self.assertEqual(pages['page7']['availableEditions'],['original'])
        self.assertEqual(pages['page7']['en'],'')
        for field,phrase in [('en','Maybe the exhaustion has been piling up.'),('ja','疲労が溜まっているんだろうか。')]:
            self.assertNotIn(phrase,pages['page2']['editions']['original'][field])
            self.assertEqual(pages['page7']['editions']['original'][field].count(phrase),1)
            self.assertEqual(pages['page2']['editions']['all-ages'][field].count(phrase),1)
    def test_final_source_restorations_have_japanese_variants(self):
        for sid,ref in [('0137','page3'),('0183','page10'),('0382','page40')]:
            page=next(p for p in self.payloads[sid]['pages'] if p['ref']==ref)
            self.assertIn('original',page['editions'])
            self.assertNotEqual(page['editions']['original']['ja'],page['editions']['all-ages']['ja'])
            self.assertGreater(len(page['editions']['original']['en']),len(page['editions']['all-ages']['en']))

if __name__=='__main__':unittest.main()
