# Fate/stay night — script browser

Public Japanese/MAO-English reader for the source-reconciled 729-script, 27,530-passage manuscript, with an independently adjudicated audit of the mirror moon English.

The script browser can display mirror moon beside the original Japanese and MAO English. The audit page publishes completed corpus totals, recurring-pattern dossiers, selected cited passages, and counterexamples. The audit evaluates mirror moon independently from the MAO translation and patch.

Build reader data with `python3 scripts/build-reader-data.py`. Run locally with `npm ci` and `npm run dev -- --host 127.0.0.1`. Production checks are `npm run typecheck` and `npm run build`.

The current patch is [v1.3.0](docs/releases/v1.3.0.md), which repairs script segmentation, paragraph boundaries, and edition-specific omissions. Run `python3 scripts/test-patch-display.py` to verify the shipped archive, display safeguards, and bound static verification report in `public/downloads/`. Native engine wrapping and playthrough have not been verified for this release. The browser reader is now at script version v1.3.0. Its release overlay synchronizes the game patch’s prose corrections and source-backed Japanese edition counterparts while preserving existing passage links. Run `python3 scripts/reader_release.py --check` and `python3 scripts/test-reader-release.py` to check the frozen projection and concordance.
