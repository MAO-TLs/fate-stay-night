# Fate/stay night — script browser

Public Japanese/MAO-English reader for the source-reconciled 729-script, 27,530-passage manuscript, with an independently adjudicated audit of the mirror moon English.

The script browser can display mirror moon beside the original Japanese and MAO English. The audit page publishes completed corpus totals, recurring-pattern dossiers, selected cited passages, and counterexamples. The audit evaluates mirror moon independently from the MAO translation and patch.

Build reader data with `python3 scripts/build-reader-data.py`. Run locally with `npm ci` and `npm run dev -- --host 127.0.0.1`. Production checks are `npm run typecheck` and `npm run build`.

The current patch is [v1.3.2](docs/releases/v1.3.2.md). It repairs 112 empty-branch spacing defects across 79 scripts without changing prose, cues, commands, or assets. The earlier [v1.3.1](docs/releases/v1.3.1.md) editorial repairs remain intact. Native engine wrapping, audible synchronization, and a full playthrough remain unverified.

Run `python3 scripts/test-patch-display.py`, `python3 scripts/reader_release.py --check`, `python3 scripts/test-reader-release.py`, `python3 scripts/test-editorial-release.py`, and `node scripts/test-english-emphasis.cjs` to verify the release. The frozen v1.3.0 overlay, v1.3.1 editorial layer, and v1.3.2 spacing layer are independently reversible; historical checks run on the exactly reconstructed parent, not on assumed current bytes.

Rebuild v1.3.1 with `python3 scripts/build-editorial-release.py path/to/v1.3.0/patch_lang_english.xp3 path/to/v1.3.1/patch_lang_english.xp3`. Then build v1.3.2 with `python3 scripts/repair-empty-branch-spacing.py path/to/v1.3.1/patch_lang_english.xp3 path/to/v1.3.2/patch_lang_english.xp3`.
