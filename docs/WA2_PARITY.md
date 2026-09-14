# Required WA2 reader and audit parity

User requirement, 2026-09-09: the eventual FSN script reader and audit must match WA2 exactly. This is a release acceptance requirement, not optional design guidance.

## Implementation reference

At integration time, identify the current published WA2 revision and its matching local source. Reuse its reader and audit components, markup, styles, and behavior. Adapt the data bindings to FSN; do not independently redesign or approximate the interface. The current local WA2 implementations are under `outputs/wa2-retranslation/`; the shared contract is `work/mao-publication-template/contract.json` relative to the workspace root. Verify their relationship to the published revision before reuse. The frozen CSS used by this initial site is not proof that later reader/audit implementations match current WA2.

Allowed differences: FSN title and approved content, three-route organization, orange color palette, and comparator name mirror moon (mirror moon in the comparison-column heading). Keep the approved light content surfaces. Do not change typography, density, card spacing, control placement, section hierarchy, or interaction patterns arbitrarily.

## Script reader

Match WA2's section and script selectors, previous/next navigation, current-script and all-script search, results and concordance presentation, comparison toggle, errors toggle, and all current reader preferences. Match compact row spacing, source references, speaker placement, column widths, wrapping, responsive breakpoints, and keyboard/focus behavior.

The ordinary Japanese/MAO two-column view has no edition headings. The comparison view has JAPANESE, MAO ENGLISH, mirror moon headings at the top right of each cell, with speaker metadata at the left when available. Do not add version or source labels.

Match exact inline error highlights, hover tooltips, focus access, single-open notes, Escape-to-close, and the fallback for evidence that cannot be positioned. Preserve URL state and direct links for section, script, search scope/query, comparison, errors, and line references, including reload and browser back/forward behavior.

## Audit

Match WA2's summary, methodology, grouped dossiers, subsection organization, evidence cards, counterexamples, navigation/filter/search controls wherever present, expansion behavior, and links into the script reader. Match the compact spacing and visual hierarchy exactly. Use only approved public findings and evidence; do not expose private critical-edition records or unfinished audit drafts.

## Acceptance

Before calling the reader or audit complete, compare FSN and the current published WA2 at identical desktop and mobile viewport sizes. Check default and comparison views, search/results, notes/highlights, dossier/evidence/counterexample views, deep links, keyboard use, and empty states. Record the WA2 revision, viewport dimensions, verified interactions, and any remaining differences. Build/type checks alone do not certify parity.

Until the approved script and audit are available, retain the current honest empty states. This document does not authorize starting the deferred audit or importing first-pass translation drafts.
