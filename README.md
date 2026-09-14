# Fate/stay night — script browser

Public Japanese/MAO-English reader for the source-reconciled 712-scene, 25,507-passage manuscript, with an independently adjudicated audit of the mirror moon English.

The script browser can display mirror moon beside the original Japanese and MAO English. The audit page publishes completed corpus totals, recurring-pattern dossiers, selected cited passages, and counterexamples. It does not make a patch-download or runtime-compatibility claim.

Build reader data with `python3 scripts/build-reader-data.py`. Run locally with `npm ci` and `npm run dev -- --host 127.0.0.1`. Production checks are `npm run typecheck` and `npm run build`.
