const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const root = path.resolve(__dirname, "..");
const comparison = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(root, "app/script/comparison-edition.ts"), "utf8"), {
  compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS}
}).outputText, {exports: comparison});
for (const [edition, expected, rejected] of [
  ["original", "mirror-moon", "remastered"],
  ["all-ages", "remastered", "mirror-moon"],
]) {
  assert.equal(comparison.comparisonFor(edition), expected);
  assert.ok(comparison.validComparison(edition, expected));
  for (const value of [rejected, null, "", "both"]) assert.ok(!comparison.validComparison(edition, value));
}
const read = p => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));
const index = read("public/data/script/index.json");
const manifest = read("public/data/comparisons/remastered/index.json");
assert.equal(manifest.edition, "all-ages");
assert.equal(manifest.scripts.length, index.scripts.length);
assert.match(manifest.witnessCommit, /^[a-f0-9]{40}$/);
assert.ok(manifest.provenanceLimit);
const counts = {};
for (const meta of index.scripts) {
  const reader = read(`public/data/script/${meta.id}.json`);
  const payload = read(`public/data/comparisons/remastered/${meta.id}.json`);
  assert.equal(payload.schema, "fsn-remastered-comparison/1");
  assert.equal(payload.scriptId, meta.id);
  const eligible = reader.pages.filter(p => !p.availableEditions || p.availableEditions.includes("all-ages"));
  assert.deepEqual(Object.keys(payload.rows).sort(), [...new Set(eligible.map(p => p.ref))].sort());
  for (const page of eligible) {
    if (eligible.filter(p => p.ref === page.ref).length > 1)
      assert.equal(payload.rows[page.ref].status, "duplicate_reference_hold");
  }
  for (const row of Object.values(payload.rows)) {
    assert.ok(["exact_japanese_text", "source_integrity_hold", "conditional_alignment_hold", "duplicate_reference_hold", "unresolved_alignment", "no_display_text"].includes(row.status));
    counts[row.status] = (counts[row.status] || 0) + 1;
    if (row.status === "exact_japanese_text") {
      assert.equal(typeof row.text, "string");
      assert.ok(row.sourceUnit.startsWith(meta.script + ":"));
    } else assert.equal(row.text, null, "Withheld alignments must not display English");
  }
}
assert.deepEqual(counts, manifest.counts);
console.log("Comparison edition isolation and every public alignment/hold verified.");
