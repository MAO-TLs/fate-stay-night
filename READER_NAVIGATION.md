# Published reader navigation

The reader retains a section selector followed by previous-script, script, and next-script controls. Corpus search is independent of the selected reading section.

- Section order: Prologue, Fate, Unlimited Blade Works, Heaven’s Feel, Last Episode.
- Within each route: numeric day, then numeric scene. The nine restored original H-scene scripts are explicitly labeled “H-scene version” and placed immediately after the corresponding base scene, where it exists. A restored-only scene occupies its natural scene position. The archival 100 offset is not presented as a scene number.
- Route epilogues follow the route’s numbered scenes. UBW has True then Good; HF has True then Normal. Last Episode is a separate final section.
- `app/script/supplemental-scripts.json` binds the nine restored scripts and six epilogues to source layer, route, and display order. Missing manuscripts are never inferred from filename patterns or presented as translated.
- Published IDs remain unchanged when order or inventory expands. Labels and display position are separate from the stable numeric deep-link ID.
- The generator validates all ordered source-page labels and binds the epilogues to their reviewed source/manuscript hashes before writing. Commented Last Episode labels do not discard their following active text.
- Landing and reader passage/script counts derive from the generated index. Search filters include Last Episode.

Validation: `python3 scripts/test-reader-data.py`, `node scripts/test-script-navigation.cjs`, `npm run typecheck`, and `npm run build`.

Publication source is committed generated JSON; manuscript and Japanese source folders live outside this site checkout. GitHub Pages builds the committed site data, not the external authoring workspace.

## Bonus scenes

Saber day6 Scene02 is labeled “Bonus scene” and sorted beside the other day6 scenes. Tiger Dojo Special appears in Extras, after Last Episode. Its 107 source units preserve Taiga/Illya/Rin speaker cues, all 15 credit commands including the spacer, and the five-unit post-credit exchange. Original engine page plus unit identifies each passage. The reader now contains 729 scripts and 27,520 source passages; all previously published IDs remain unchanged.
