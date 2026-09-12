const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const catalog = require('../app/script/supplemental-scripts.json');
const index = require('../public/data/script/index.json');
const source = fs.readFileSync(path.join(__dirname,'../app/script/script-labels.ts'),'utf8');
const compiled = ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
const mod={exports:{}};
new Function('require','module','exports',compiled)(()=>catalog,mod,mod.exports);
const {scriptTitle,compareScripts}=mod.exports;
const referenceSource = fs.readFileSync(path.join(__dirname,'../app/script/reference-label.ts'),'utf8');
const referenceCompiled = ts.transpileModule(referenceSource,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const referenceMod={exports:{}};
new Function('require','module','exports',referenceCompiled)(require,referenceMod,referenceMod.exports);
const {referenceLabel}=referenceMod.exports;
assert.equal(referenceLabel('page0'),'1');
assert.equal(referenceLabel('page59'),'60');
assert.equal(referenceLabel('0712-page3'),'4');
assert.equal(referenceLabel('page0-unit000'),'1');
const ordered=[...index.scripts].sort(compareScripts);
assert.equal(new Set(ordered.map(s=>s.id)).size,729);
for(const item of ordered) assert.match(scriptTitle(item.script),/[A-Za-z]/);
for(const [name,entry] of Object.entries(catalog)) {
  const pos=ordered.findIndex(s=>s.script===name);
  assert.ok(pos>=0);
  assert.equal(ordered[pos].route,entry.route);
  if(entry.layer==='restored') {
    assert.match(scriptTitle(name),/\(H-scene version\)$/);
    assert.ok(scriptTitle(name).includes(`Scene ${String(entry.scene).padStart(2,'0')}`));
    const base=name.replace(/-\d+$/,`-${String(entry.scene).padStart(2,'0')}`);
    const basePos=ordered.findIndex(s=>s.script===base);
    if(basePos>=0) assert.equal(pos,basePos+1,`${name} must immediately follow its base version`);
  }
}
for(const [route,endings] of [['fate',['セイバーエピローグ']],['ubw',['凛エピローグ2','凛エピローグ']],['hf',['桜エピローグ','桜エピローグ2']]]) {
  assert.deepEqual(ordered.filter(s=>s.route===route).slice(-endings.length).map(s=>s.script),endings);
}
assert.equal(ordered.at(-2).script,'ラストエピソード');
assert.equal(ordered.at(-1).script,'タイガー道場すぺしゃる');
assert.equal(ordered.at(-1).route,'extras');
const concordance=JSON.parse(fs.readFileSync(path.join(__dirname,'../public/data/script/concordance.json')));
assert.equal(concordance.length,27529);
assert.equal(index.pageCount,27529);
for(const item of index.scripts) {
  const payload=JSON.parse(fs.readFileSync(path.join(__dirname,`../public/data/script/${item.id}.json`)));
  assert.equal(payload.script,item.script);
  assert.equal(payload.route,item.route);
  assert.equal(payload.pages.length,item.pages);
  assert.deepEqual(
    concordance.filter(p=>p.scriptId===item.id).map(({scriptId,script,route,title,...page})=>page),
    payload.pages.map(({mirrorMoon,...page})=>page)
  );
}
const prologue=JSON.parse(fs.readFileSync(path.join(__dirname,'../public/data/script/0000.json')));
assert.match(prologue.pages[0].mirrorMoon,/thrust like lightning/i);
assert.ok(!Object.hasOwn(concordance[0],'mirrorMoon'));
console.log('PASS: 729 labels, restored-scene adjacency, ending order, Last Episode section, and 27,529 concordance bindings.');

const tigerMeta=index.scripts.find(s=>s.script==='タイガー道場すぺしゃる');
const tiger=require('../public/data/script/'+tigerMeta.id+'.json');
assert.equal(tiger.pages.length,107);
assert.deepEqual(tiger.pages.filter(p=>p.speaker==='Rin').map(p=>p.ref),['page0-unit046','page0-unit053','page0-unit060']);
assert.equal(tiger.pages[87].kind,'credit');
assert.equal(tiger.pages[101].en,'TYPE-MOON’s Dark Side');
assert.equal(tiger.pages[102].speaker,'Taiga');
assert.equal(tiger.pages[99].en,'');
assert.match(tiger.pages[24].en,/oshiruko and zenzai/);
assert.ok(tiger.pages[64].en.endsWith(tiger.pages[105].en));
assert.match(scriptTitle('セイバールート六日目-02'),/Bonus scene/);
console.log('PASS: Tiger Dojo speaker cues, credits, post-credit scene, and callback bindings.');
