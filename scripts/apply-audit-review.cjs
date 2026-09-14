// Rebuild publication from the frozen pre-review snapshot and exact review IDs.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const site = path.resolve(__dirname, '..');
const snapshot = 'c0efd34d9d3275d994feed777041d8985f03cc5a';
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const original = file => JSON.parse(execFileSync('git', ['show', `${snapshot}:${file}`], {cwd: site, maxBuffer: 32 * 1024 * 1024}));
const write = (file, value) => { fs.mkdirSync(path.dirname(file), {recursive:true}); fs.writeFileSync(file, JSON.stringify(value) + '\n'); };
const reviewFile = path.join(__dirname, 'data/audit-review.json');
if (process.argv[2]) {
  const records = read(process.argv[2]);
  write(reviewFile, records.map(({review}) => ({id:review.id, verdict:review.verdict, reason:review.reason})));
}
const reviews = read(reviewFile);
const byId = new Map(reviews.map(r => [r.id, r]));
const counts = {keep:0,reject:0,revise:0,needs_context:0};
for (const r of reviews) {
  if (!(r.verdict in counts) || !r.reason) throw Error(`Invalid review ${r.id}`);
  counts[r.verdict]++;
}
if (reviews.length !== 18514 || byId.size !== reviews.length) throw Error('Incomplete review coverage');
const retained = id => {if (!byId.has(id)) throw Error(`Unreviewed finding ${id}`); return byId.get(id).verdict === 'keep';};
const base = 'public/data/audit/';
const index = original(base + 'findings/index.json');
const dossiers = original(base + 'dossiers.json');
const known = new Set(index.unmapped.map(f=>f.id));
const citationCandidates = new Map(index.unmapped.map(f => [f.id, f]));
for (const route of index.routes) {
  const file = base + `findings/${route.scriptId}.json`;
  const payload = original(file);
  payload.findings.forEach(f=>known.add(f.id));
  payload.findings = payload.findings.filter(f=>retained(f.id));
  const script = read(path.join(site, 'public/data/script', `${route.scriptId}.json`)).script;
  payload.findings.forEach(f => citationCandidates.set(f.id, {...f, script}));
  payload.findingCount = payload.findings.length;
  route.findingCount = payload.findingCount;
  write(path.join(site,file),payload);
}
if (known.size !== byId.size || [...known].some(id=>!byId.has(id))) throw Error('Snapshot/review IDs differ');
index.unmapped = index.unmapped.filter(f=>retained(f.id));
index.totalFindings = counts.keep;
index.mappedFindings = index.routes.reduce((n,r)=>n+r.findingCount,0);
index.unmappedFindings = index.unmapped.length;
index.withheldBorderlineCount = dossiers.withheldBorderlineCount + counts.revise;
index.needsContextCount = counts.needs_context;
index.withdrawnFindingCount = counts.reject;
index.reviewedFindingCount = reviews.length;
if (index.mappedFindings + index.unmappedFindings !== counts.keep) throw Error('Publication count mismatch');
for (const group of dossiers.groups) {
  for (const d of group.dossiers) {
    d.findingIds = d.findingIds.filter(retained);
    d.examples = d.examples.filter(e=>retained(e.findingId)).slice(0, 8);
    const cited = new Set(d.examples.map(e => e.findingId));
    for (const id of d.findingIds) {
      if (d.examples.length >= 8) break;
      if (cited.has(id)) continue;
      const f = citationCandidates.get(id);
      if (!f || !f.evidenceJa || !f.highlight || !f.explanation) continue;
      d.examples.push({
        ref: `${f.script}:${f.ref}`, findingId: f.id,
        japanese: f.evidenceJa, mirrorMoon: f.highlight,
        note: f.explanation, category: f.category, status: f.status,
      });
      cited.add(id);
    }
    d.confirmedCount = d.findingIds.length;
    d.exampleCount = d.examples.length;
    d.diagnostic = `${d.confirmedCount.toLocaleString('en-US')} retained findings after re-review; ${d.exampleCount} cited passages.`;
  }
}
dossiers.corpusConfirmedFindingCount = counts.keep;
dossiers.withheldBorderlineCount = index.withheldBorderlineCount;
dossiers.previouslyWithheldBorderlineCount = 36;
dossiers.revisionNeededCount = counts.revise;
dossiers.needsContextCount = counts.needs_context;
dossiers.withdrawnFindingCount = counts.reject;
dossiers.reviewedFindingCount = reviews.length;
const all = dossiers.groups.flatMap(g=>g.dossiers);
dossiers.citedPassageCount = all.reduce((n,d)=>n+d.examples.length,0);
dossiers.uniqueCitedFindingCount = new Set(all.flatMap(d=>d.examples.map(e=>e.findingId))).size;
write(path.join(site,base+'dossiers.json'),dossiers);
write(path.join(site,base+'findings/index.json'),index);
console.log(JSON.stringify({retained:counts.keep,mapped:index.mappedFindings,borderline:index.withheldBorderlineCount,needsContext:counts.needs_context,withdrawn:counts.reject,citedPassages:dossiers.citedPassageCount}));
