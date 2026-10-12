# Fate/stay night — script browser

Public Japanese/MAO-English reader for the source-reconciled 729-script, 27,530-passage manuscript, with an independently adjudicated audit of the mirror moon English.

The script browser can display mirror moon beside the original Japanese and MAO English. The audit page publishes completed corpus totals, recurring-pattern dossiers, selected cited passages, and counterexamples. The audit evaluates mirror moon independently from the MAO translation and patch.

Build reader data with `python3 scripts/build-reader-data.py`. Run locally with `npm ci` and `npm run dev -- --host 127.0.0.1`. Production checks are `npm run typecheck` and `npm run build`.

The current patch is [v1.2.1](docs/releases/v1.2.1.md), a display-only hotfix. Run `python3 scripts/test-patch-display.py` to verify the shipped archive and its display safeguards. The download manifest and bounded native display evidence are in `public/downloads/`.
