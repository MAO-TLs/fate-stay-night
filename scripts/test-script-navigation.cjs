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
const ordered=[...index.scripts].sort(compareScripts);
assert.equal(new Set(ordered.map(s=>s.id)).size,727);
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
assert.equal(ordered.at(-1).script,'ラストエピソード');
assert.equal(ordered.at(-1).route,'last-episode');
const concordance=JSON.parse(fs.readFileSync(path.join(__dirname,'../public/data/script/concordance.json')));
assert.equal(concordance.length,27410);
assert.equal(index.pageCount,27410);
for(const item of index.scripts) {
  const payload=JSON.parse(fs.readFileSync(path.join(__dirname,`../public/data/script/${item.id}.json`)));
  assert.equal(payload.script,item.script);
  assert.equal(payload.route,item.route);
  assert.equal(payload.pages.length,item.pages);
  assert.deepEqual(concordance.filter(p=>p.scriptId===item.id).map(({scriptId,script,route,title,...page})=>page),payload.pages);
}
console.log('PASS: 727 labels, restored-scene adjacency, ending order, Last Episode section, and 27,410 concordance bindings.');
