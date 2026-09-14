const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const {createElement} = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const root = path.resolve(__dirname, '..');
const component = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root,'app/script/EnglishText.tsx'),'utf8'), {
  compilerOptions: {target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX},
}).outputText,{exports:component,require});
const render = text => renderToStaticMarkup(createElement(component.EnglishText,{text}));
assert.equal(render('a *female creature* as though'),'a <em>female creature</em> as though');
assert.equal(render('*I* said *you*,\nnot me.'),'<em>I</em> said <em>you</em>,\nnot me.');
for(const text of ['plain text','unmatched *word','***','**bold**','a * spaced * word','line *one\ntwo*','\\*literal*']) assert.equal(render(text),text);
assert.equal(render('*<script>*'),'<em>&lt;script&gt;</em>');
const page = JSON.parse(fs.readFileSync(path.join(root,'public/data/script/0027.json'))).pages.find(p=>p.ref==='page21');
assert(render(page.en).includes('<em>female creature</em>'));
assert(!render(page.en).includes('*female creature*'));
// Both reader and concordance results use the shared ScriptLine component.
const reader=fs.readFileSync(path.join(root,'app/script/ScriptReader.tsx'),'utf8');
assert(reader.includes('<EnglishText text={displayEnglish(page.en) || "—"}/>'));
assert(reader.includes('<ScriptLine id={page.ref}'));
console.log('PASS: manuscript italics, literal stars, line breaks, HTML escaping, screenshot passage, and shared reader wiring');
