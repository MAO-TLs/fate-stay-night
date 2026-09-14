const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const site = path.resolve(__dirname,'..');
const read = file => JSON.parse(fs.readFileSync(path.join(site,file)));
const review = read('scripts/data/audit-review.json');
const kept = new Set(review.filter(r=>r.verdict==='keep').map(r=>r.id));
const index = read('public/data/audit/findings/index.json');
const ds = read('public/data/audit/dossiers.json');
const records = [...index.unmapped];
for (const route of index.routes) {
  const data = read(`public/data/audit/findings/${route.scriptId}.json`);
  assert.equal(data.findings.length,route.findingCount);
  assert.equal(data.findingCount,route.findingCount);
  const pages = new Set(read(`public/data/script/${route.scriptId}.json`).pages.map(p=>p.ref));
  data.findings.forEach(f=>assert(pages.has(f.ref),f.id));
  records.push(...data.findings);
}
assert.deepEqual(new Set(records.map(r=>r.id)),kept);
assert.equal(records.length,kept.size);
assert.equal(index.totalFindings,8248);
assert.equal(ds.corpusConfirmedFindingCount,index.totalFindings);
assert.equal(ds.withheldBorderlineCount,2377);
assert.equal(ds.needsContextCount,154);
assert.equal(ds.withdrawnFindingCount,7771);
assert(!records.some(r=>r.id==='fsn-mm-000064'));
let cited=0;
for (const d of ds.groups.flatMap(g=>g.dossiers)) {
  assert.equal(d.confirmedCount,d.findingIds.length);
  assert.equal(d.exampleCount,d.examples.length);
  d.findingIds.forEach(id=>assert(kept.has(id),id));
  d.examples.forEach(e=>assert(kept.has(e.findingId),e.findingId));
  cited+=d.examples.length;
}
assert.equal(ds.citedPassageCount,cited);
console.log('PASS: exact publication membership, totals, page bindings, dossier references, and false-positive removal');
