const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const labels = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root, "app/script/script-labels.ts"), "utf8"), {
  compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop:true}
}).outputText, {exports:labels, require:()=>JSON.parse(fs.readFileSync(path.join(root,"app/script/supplemental-scripts.json")))});
const scripts = JSON.parse(fs.readFileSync(path.join(root,"public/data/script/index.json"))).scripts;
for (const edition of ["original","all-ages"]) {
  const choices = labels.editionScripts(scripts,edition);
  assert.equal(choices.length, scripts.length - 9);
  assert.equal(new Set(choices.map(x=>labels.sceneKey(x.script))).size,choices.length);
  for (const choice of choices) {
    const parts = labels.editionParts(scripts,choice.script,edition);
    assert.ok(parts.length);
    assert.ok(parts.every(x=>fs.existsSync(path.join(root,"public/data/script",x.id+".json"))));
  }
}
for (const [base, original] of [
  ["セイバールート十四日目-11",["セイバールート十四日目-111","セイバールート十四日目-101"]],
  ["凛ルート十四日目-08",["凛ルート十四日目-108","凛ルート十四日目-130"]]
]) {
  assert.deepEqual(Array.from(labels.editionParts(scripts,base,"original"),x=>x.script),original);
  assert.deepEqual(Array.from(labels.editionParts(scripts,base,"all-ages"),x=>x.script),[base]);
}
console.log("Edition grouping: every script accounted for; both multipart sequences verified.");
const projection = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root, "app/script/edition-text.ts"), "utf8"), {
  compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS}
}).outputText, {exports:projection});
const concordance = JSON.parse(fs.readFileSync(path.join(root,"public/data/script/concordance.json")));
let variants = 0;
const additions=JSON.parse(fs.readFileSync(path.join(root,"app/script/edition-additions.json")));
const exclusions=JSON.parse(fs.readFileSync(path.join(root,"app/script/edition-exclusions.json")));
for (const exclusion of exclusions) {
  const meta=scripts.find(s=>s.script===exclusion.script);
  assert.ok(meta,`Unknown exclusion script: ${exclusion.script}`);
  const sourcePath=path.join(root,"..","source/reader/jp/base",exclusion.script+".ks");
  const sourceBytes=fs.readFileSync(sourcePath);
  assert.equal(crypto.createHash("sha256").update(sourceBytes).digest("hex"),exclusion.source_sha256,`Stale exclusion source binding: ${exclusion.script}:${exclusion.line}`);
  const source=sourceBytes.toString("utf8").split(/\r?\n/);
  assert.ok(source[exclusion.line-1]?.startsWith(";"),`Exclusion is not bound to a source comment: ${exclusion.script}:${exclusion.line}`);
  assert.ok(exclusion.reason.length>20,`Exclusion requires a substantive review reason: ${exclusion.script}:${exclusion.line}`);
  assert.ok(!additions.some(a=>a.script===exclusion.script && a.source_lines.some(line=>line.line===exclusion.line)),`Exclusion overlaps an edition addition: ${exclusion.script}:${exclusion.line}`);
}
for (const script of scripts) {
  const data = JSON.parse(fs.readFileSync(path.join(root,"public/data/script",script.id+".json")));
  for (const page of data.pages) {
    if (!page.editions) {
      assert.equal(projection.editionText(page,"original"),page);
      assert.equal(projection.editionText(page,"all-ages"),page);
      continue;
    }
    variants++;
    const hit = concordance.find(x=>x.scriptId===script.id && x.ref===page.ref);
    assert.ok(hit,`Missing concordance entry: ${script.id}:${page.ref}`);
    assert.deepEqual(hit.editions,page.editions);
    for (const edition of ["original","all-ages"]) {
      if (!projection.editionAvailable(page,edition)) {
        assert.equal(edition,"all-ages");
        assert.equal(page.editionVirtual,true);
        assert.equal(page.editions[edition],undefined);
        assert.equal(projection.editionAvailable(hit,edition),false);
        continue;
      }
      const visible = projection.editionText(page,edition);
      assert.equal(visible.en,page.editions[edition].en);
      assert.equal(visible.ja,page.editions[edition].ja);
      assert.equal(visible.ref,page.ref);
      assert.equal(projection.editionText(hit,edition).en,visible.en);
    }
    if (page.editionVirtual) continue;
    const alignment=additions.find(a=>a.script===script.script && a.ref===page.ref && a.existing_english);
    if (alignment) {
      const expected=page.en.split("\n\n");
      assert.deepEqual(expected.splice(alignment.insert_after_paragraph,alignment.existing_english.length,...(alignment.all_ages_replacement || [])),alignment.existing_english);
      assert.equal(page.editions["all-ages"].en,expected.join("\n\n"));
      assert.equal(page.editions.original.en,page.en,"Original must reuse existing English exactly");
    } else assert.equal(page.editions["all-ages"].en,page.en);
  }
}
assert.ok(variants >= 2);
for (const addition of additions) {
  const meta=scripts.find(s=>s.script===addition.script);
  const data=JSON.parse(fs.readFileSync(path.join(root,"public/data/script",meta.id+".json")));
  const page=data.pages.find(p=>p.ref===addition.ref);
  assert.ok(page,`Missing addition page: ${addition.script}:${addition.ref}`);
  if (addition.virtual) {
    assert.equal(page.editionVirtual,true);
    assert.deepEqual(page.availableEditions,["original"]);
    assert.equal(page.en,"");
    assert.equal(page.ja,"");
    assert.equal(page.editions.original.en,addition.english);
    assert.equal(projection.editionAvailable(page,"original"),true);
    assert.equal(projection.editionAvailable(page,"all-ages"),false);
    for (const line of addition.source_lines) {
      const plain=line.raw.slice(1).replace(/\[[^\]]*\]/g,"").replace(/[\s　]/g,"");
      assert.ok(page.editions.original.ja.replace(/[\s　]/g,"").includes(plain));
    }
    continue;
  }
  if (addition.existing_english) {
    assert.equal(page.editions.original.en,page.en);
    for(const line of addition.source_lines) {
      const plain=line.raw.slice(1).replace(/\[[^\]]*\]/g,"").trim();
      assert.ok(page.editions.original.ja.includes(plain));
      assert.ok(!page.editions["all-ages"].ja.includes(plain));
    }
    continue;
  }
  const original=page.editions.original.en.split("\n\n");
  const count=addition.reuse ? addition.reuse.paragraphs+1 : addition.english.split("\n\n").length;
  original.splice(addition.insert_after_paragraph,count);
  const shared=page.en.split("\n\n");
  shared.splice(addition.insert_after_paragraph,addition.replace_paragraphs || 0);
  assert.equal(original.join("\n\n"),shared.join("\n\n"),"Edition insertion must preserve every shared paragraph byte-for-byte");
  for (const removed of addition.omitted_source_lines || []) {
    const plain=removed.raw.replace(/\[[^\]]*\]/g,"").trim();
    assert.ok(!page.editions.original.ja.split("\n").map(s=>s.trim()).includes(plain),"Mutually exclusive Japanese lines must not be concatenated");
  }
  if (addition.reuse) {
    const donorMeta=scripts.find(s=>s.script===addition.reuse.script);
    const donor=JSON.parse(fs.readFileSync(path.join(root,"public/data/script",donorMeta.id+".json"))).pages.find(p=>p.ref===addition.reuse.ref);
    assert.deepEqual(page.editions.original.en.split("\n\n").slice(1,4),donor.editions.original.en.split("\n\n").slice(1,4));
  }
}
const chamber = JSON.parse(fs.readFileSync(path.join(root,"public/data/script/0496.json")));
const originalPassage = ref => projection.editionText(chamber.pages.find(p=>p.ref===ref),"original").en;
assert.equal((originalPassage("page13").match(/After a long silence/g)||[]).length,1);
assert.ok(originalPassage("page13").includes("The insects recede"));
assert.ok(!originalPassage("page13").includes("The monsters’ presences"));
assert.deepEqual(originalPassage("page13").split("\n\n").slice(0,3),chamber.pages.find(p=>p.ref==="page13").en.split("\n\n").slice(0,3));
assert.ok(originalPassage("page0").includes("someone being dragged in."));
assert.ok(originalPassage("page15").includes("breeding pool of insects—the black Servant"));
assert.ok(!originalPassage("page15").includes("monsters—the black Servant"));
for (const [name,ref,phrases] of [
  ["セイバールート一日目-07","page0",["I walk through the town at night.","starry winter sky","It must be around seven thirty.","not another soul outside"]],
  ["セイバールート四日目-04","page21",["I don't want to fight her.","the girl I admired at school","The Rin Tohsaka before me","explain it to myself"]],
  ["凛ルート六日目-14","page4",["There is only one.","The thread is so fine","If the enemy controlling it deserves praise"]],
  ["凛ルート十一日目-03","page9",["My throat moves","If anything is making too much noise","It is past pounding now"]],
  ["凛ルート十四日目-21","page9",["Yes, you were.","She scolds me, looking offended.","her indignation brings me"]],
  ["凛ルート十四日目-34","page60",["Then let us grade your work.","I will not allow a single copy","Gilgamesh raises his arm."]]
]) {
  const meta=scripts.find(s=>s.script===name);
  const data=JSON.parse(fs.readFileSync(path.join(root,"public/data/script",meta.id+".json")));
  const text=projection.editionText(data.pages.find(p=>p.ref===ref),"original").en;
  let previous=-1;
  for (const phrase of phrases) {
    const index=text.indexOf(phrase);
    assert.ok(index>previous,`${name}: missing or out-of-order ${phrase}`);
    assert.equal(text.indexOf(phrase,index+1),-1,`${name}: duplicated ${phrase}`);
    previous=index;
  }
}
const sample={ja:"shared",jaRuby:"old ruby",en:"shared",editions:{original:{ja:"variant",en:"variant"}}};
assert.equal(projection.editionText(sample,"original").jaRuby,"variant");
assert.equal(sample.jaRuby,"old ruby");

const sakuraMorningMeta=scripts.find(s=>s.script==="桜ルート十日目-06");
const sakuraMorning=JSON.parse(fs.readFileSync(path.join(root,"public/data/script",sakuraMorningMeta.id+".json")));
const originalRefs=sakuraMorning.pages.filter(page=>projection.editionAvailable(page,"original")).map(page=>page.ref);
const allAgesRefs=sakuraMorning.pages.filter(page=>projection.editionAvailable(page,"all-ages")).map(page=>page.ref);
assert.deepEqual(originalRefs.slice(0,15),["page0","page1","page2","page3","page4","page5","page6","page7","page8","page9","page10","page11","page12","page13","page14"]);
assert.deepEqual(allAgesRefs.slice(0,9),["page0","page1","page2","page8","page9","page10","page11","page12","page14"]);
assert.equal(sakuraMorningMeta.editionPages.original,sakuraMorningMeta.editionPages["all-ages"]+6);
for (const [ref,text] of [
  ["page3","At any rate, that blew the sleepiness out of me in an instant."],
  ["page4","There’s no one beside me. All I can see is my own arm, sprawled there limply."],
  ["page5","Knowing Sakura, she’s probably getting everything ready for the morning while leaving me to sleep."],
  ["page6","The instant I do, a slight wave of dizziness hits me."],
  ["page7","“…Oof. My body really does feel heavy.”"],
  ["page13","I give the key a mighty turn, kick down the goddamn heavy accelerator, and charge into the living room where Sakura is."]
]) {
  const page=sakuraMorning.pages.find(page=>page.ref===ref);
  assert.ok(page.editions.original.en.includes(text));
  const hit=concordance.find(hit=>hit.scriptId===sakuraMorningMeta.id && hit.ref===ref);
  assert.deepEqual(hit.availableEditions,["original"]);
  assert.equal(projection.editionAvailable(hit,"all-ages"),false);
}
console.log(`Embedded editions: ${variants} bound passages agree in reader and concordance; shared text preserved.`);
