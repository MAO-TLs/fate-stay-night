"use client";
import { referenceLabel } from "./reference-label";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { displayEnglish, displayJapanese } from "./display-text";
import { compareScripts, sceneTitle as scriptTitle, sceneKey, isOriginalVariant, editionScripts, editionParts, type Edition } from "./script-labels";
import { JapaneseText } from "./JapaneseText";
import { EnglishText } from "./EnglishText";
import { editionAvailable, editionText, type EditionPassage } from "./edition-text";

type ScriptMeta = {id: string; script: string; route: string; title: string; pages: number; editionPages?: Record<Edition, number>};
type Page = EditionPassage & {ref: string; speaker?: string | null; kind?: string; mirrorMoon?: string};
type ScriptData = Omit<ScriptMeta, "pages"> & {pages: Page[]};
type IndexData = {scripts: ScriptMeta[]; scriptCount: number; pageCount: number};
type ConcordancePage = Page & {scriptId: string; script: string; route: string; title: string};
type SearchScope = "script" | "corpus";
type AuditFinding = {id: string; ref: string; category: string; status: string; highlight: string; evidenceJa: string; governingReading: string; explanation: string; dossiers: string[]};
type AuditPayload = {schema: string; scriptId: string; findingCount: number; findings: AuditFinding[]};

const routeNames: Record<string, string> = {prologue: "Prologue", fate: "Fate", ubw: "Unlimited Blade Works", hf: "Heaven's Feel", "last-episode": "Last Episode", extras: "Extras"};
const resultLimit = 200;
const readerDataRevision = "2026-09-13-mirror-moon-2";

export function ScriptReader() {
  const [index, setIndex] = useState<IndexData | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [edition, setEdition] = useState<Edition>("original");
  const [showMirrorMoon, setShowMirrorMoon] = useState(false);
  const [showAuditFindings, setShowAuditFindings] = useState(false);
  const [urlStateReady, setUrlStateReady] = useState(false);
  const [auditFindings, setAuditFindings] = useState<AuditFinding[]>([]);
  const [activeFindingId, setActiveFindingId] = useState("");
  const [route, setRoute] = useState("prologue");
  const [data, setData] = useState<ScriptData | null>(null);
  const [scope, setScope] = useState<SearchScope>("script");
  const [scriptQuery, setScriptQuery] = useState("");
  const [corpusQuery, setCorpusQuery] = useState("");
  const [concordance, setConcordance] = useState<ConcordancePage[] | null>(null);
  const [corpusRoute, setCorpusRoute] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`../data/script/index.json?v=${readerDataRevision}`).then(r => {
      if (!r.ok) throw new Error("The script index could not be loaded.");
      return r.json();
    }).then((value: IndexData) => {
      value = {...value, scripts: [...value.scripts].sort(compareScripts)};
      setIndex(value);
      const params = new URLSearchParams(window.location.search);
      const requested = params.get("script");
      const requestedRoute = params.get("section");
      const requestedItem = value.scripts.find(x => x.id === requested);
      const chosenEdition: Edition = params.get("edition") === "all-ages" ? "all-ages" : params.get("edition") === "original" ? "original" : requestedItem && !isOriginalVariant(requestedItem.script) && value.scripts.some(x => isOriginalVariant(x.script) && sceneKey(x.script) === requestedItem.script) ? "all-ages" : "original";
      setEdition(chosenEdition);
      setShowMirrorMoon(chosenEdition === "original" && params.get("compare") === "mirror-moon");
      setShowAuditFindings(chosenEdition === "original" && params.get("compare") === "mirror-moon" && params.get("errors") === "mirror-moon");
      setUrlStateReady(true);
      const choices = editionScripts(value.scripts, chosenEdition);
      const initial = value.scripts.find(x => x.id === requested) ?? value.scripts.find(x => x.route === requestedRoute) ?? value.scripts[0];
      const initialParts = editionParts(value.scripts, initial.script, chosenEdition);
      if (initialParts.findIndex(x => x.id === requested) > 0 && window.location.hash) {
        const url = new URL(window.location.href);
        if (!url.hash.slice(1).startsWith(requested + "-")) url.hash = requested + "-" + url.hash.slice(1);
        window.history.replaceState({}, "", url);
      }
      setSelectedId(choices.find(x => sceneKey(x.script) === sceneKey(initial.script))?.id ?? initial.id);
      setRoute(initial.route);
    }).catch(reason => setError(String(reason)));
  }, []);

  useEffect(() => {
    if (!selectedId || !index) return;
    let cancelled = false;
    setData(null);
    const selected = index.scripts.find(x => x.id === selectedId);
    if (!selected) return;
    const parts = editionParts(index.scripts, selected.script, edition);
    Promise.all(parts.map(part => fetch(`../data/script/${part.id}.json?v=${readerDataRevision}`).then(r => {
      if (!r.ok) throw new Error("This script could not be loaded.");
      return r.json();
    }))).then((values: ScriptData[]) => {
      if (cancelled) return;
      const value = {...values[0], pages: values.flatMap((part, i) => part.pages.filter(page => editionAvailable(page, edition)).map(page => ({...editionText(page, edition), ref:i ? part.id + "-" + page.ref : page.ref})))};
      setData(value);
      const url = new URL(window.location.href);
      url.searchParams.set("script", selectedId);
      url.searchParams.set("edition", edition);
      url.searchParams.delete("section");
      window.history.replaceState({}, "", url);
      requestAnimationFrame(() => {
        if (!cancelled && url.hash) document.getElementById(decodeURIComponent(url.hash.slice(1)))?.scrollIntoView({block:"start"});
      });
    }).catch(reason => { if (!cancelled) setError(String(reason)); });
    return () => { cancelled = true; };
  }, [selectedId, edition, index]);

  useEffect(() => {
    if (!selectedId || !index || edition !== "original" || !showAuditFindings) {
      setAuditFindings([]);
      setActiveFindingId("");
      return;
    }
    let cancelled = false;
    const selected = index.scripts.find(x => x.id === selectedId);
    if (!selected) return;
    const parts = editionParts(index.scripts, selected.script, edition);
    Promise.all(parts.map((part, i) => fetch(`../data/audit/findings/${part.id}.json?v=${readerDataRevision}`).then(async r => {
      if (r.status === 404) return [];
      if (!r.ok) throw new Error("The audit annotations could not be loaded.");
      const payload = await r.json() as AuditPayload;
      if (payload.schema !== "fsn-mirror-moon-editorial-errors/1") throw new Error("The audit annotation format is not supported.");
      return payload.findings.map(finding => ({...finding, ref: i ? part.id + "-" + finding.ref : finding.ref}));
    }))).then(values => { if (!cancelled) setAuditFindings(values.flat()); }).catch(reason => { if (!cancelled) setError(String(reason)); });
    return () => { cancelled = true; };
  }, [selectedId, edition, index, showAuditFindings]);

  useEffect(() => {
    if (!urlStateReady) return;
    const url = new URL(window.location.href);
    if (edition === "original" && showMirrorMoon) url.searchParams.set("compare", "mirror-moon");
    else url.searchParams.delete("compare");
    if (edition === "original" && showAuditFindings) url.searchParams.set("errors", "mirror-moon");
    else url.searchParams.delete("errors");
    window.history.replaceState({}, "", url);
  }, [edition, showMirrorMoon, showAuditFindings, urlStateReady]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setActiveFindingId("");
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  useEffect(() => {
    if (scope !== "corpus" || concordance) return;
    fetch(`../data/script/concordance.json?v=${readerDataRevision}`).then(r => r.json()).then(setConcordance).catch(reason => setError(String(reason)));
  }, [scope, concordance]);

  const choices = useMemo(() => editionScripts(index?.scripts ?? [], edition), [index, edition]);
  const routeScripts = choices.filter(x => x.route === route);
  const selectedEditionPageCount = choices.reduce((total, item) => total + editionParts(index?.scripts ?? [], item.script, edition).reduce((sum, part) => sum + (part.editionPages?.[edition] ?? part.pages), 0), 0);
  function scenePageCount(script: string) {
    return editionParts(index?.scripts ?? [], script, edition).reduce((sum, part) => sum + (part.editionPages?.[edition] ?? part.pages), 0);
  }
  const currentPosition = choices.findIndex(x => x.id === selectedId);
  const editionIds = useMemo(() => new Set(choices.flatMap(x => editionParts(index?.scripts ?? [], x.script, edition).map(p => p.id))), [choices, index, edition]);
  function changeEdition(next: Edition) {
    const current = index?.scripts.find(x => x.id === selectedId);
    const counterpart = editionScripts(index?.scripts ?? [], next).find(x => current && sceneKey(x.script) === sceneKey(current.script));
    setEdition(next);
    if (next !== "original") { setShowMirrorMoon(false); setShowAuditFindings(false); setActiveFindingId(""); }
    if (counterpart) setSelectedId(counterpart.id);
    const url = new URL(window.location.href);
    url.searchParams.set("edition", next);
    url.hash = "";
    window.history.replaceState({}, "", url);
  }
  const visiblePages = useMemo(() => {
    if (!data) return [];
    const needle = scriptQuery.trim().toLocaleLowerCase();
    return needle ? data.pages.filter(page => `${page.ja}\n${page.en}`.toLocaleLowerCase().includes(needle)) : data.pages;
  }, [data, scriptQuery, edition]);
  const findingsByPage = useMemo(() => {
    const out = new Map<string, AuditFinding[]>();
    for (const finding of auditFindings) out.set(finding.ref, [...(out.get(finding.ref) ?? []), finding]);
    return out;
  }, [auditFindings]);
  const editionConcordance = useMemo(() => concordance?.filter(page => editionIds.has(page.scriptId) && editionAvailable(page, edition)).map(page => editionText(page, edition)) ?? [], [concordance, editionIds, edition]);
  const corpusMatches = useMemo(() => {
    const needle = corpusQuery.trim().toLocaleLowerCase();
    if (!needle || !concordance) return [];
    return editionConcordance.filter(page => (corpusRoute === "all" || page.route === corpusRoute) && `${page.ja}\n${page.en}`.toLocaleLowerCase().includes(needle));
  }, [concordance, corpusQuery, corpusRoute, editionConcordance]);

  function move(offset: number) {
    if (!index || currentPosition < 0) return;
    const next = choices[currentPosition + offset];
    if (next) { setRoute(next.route); setSelectedId(next.id); setScriptQuery(""); }
  }

  const resultStatus = scope === "script"
    ? data ? `${visiblePages.length.toLocaleString()} ${scriptQuery.trim() ? "matching " : ""}passages` : "Loading script…"
    : !corpusQuery.trim() ? `${selectedEditionPageCount.toLocaleString() ?? "…"} passages ready to search` : !concordance ? "Loading complete concordance…" : `${corpusMatches.length.toLocaleString()} matching passages`;

  return <section className="reader-shell shell compact">
    <div id="reader-controls" className="reader-controls-anchor" aria-hidden="true"/><div className="reader-controls">
      <div className="control"><label htmlFor="route">Section</label><select id="route" value={route} disabled={scope === "corpus"} onChange={event => {
        const nextRoute = event.target.value; setRoute(nextRoute);
        const first = choices.find(x => x.route === nextRoute); if (first) setSelectedId(first.id);
      }}>{Object.entries(routeNames).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></div>
      <div className="control"><label htmlFor="script">Script</label><div className="script-picker"><button onClick={() => move(-1)} disabled={scope === "corpus" || currentPosition <= 0} aria-label="Previous script">←</button><select id="script" value={selectedId} disabled={scope === "corpus"} onChange={event => setSelectedId(event.target.value)}>{routeScripts.map(item => <option key={item.id} value={item.id}>{scriptTitle(item.script)} · {scenePageCount(item.script).toLocaleString()} passages</option>)}</select><button onClick={() => move(1)} disabled={scope === "corpus" || !index || currentPosition >= choices.length - 1} aria-label="Next script">→</button></div></div>
      <fieldset className="search-scope"><legend>Search scope</legend><div className="scope-options"><label><input type="radio" name="search-scope" checked={scope === "script"} onChange={() => setScope("script")}/><span>This script</span></label><label><input type="radio" name="search-scope" checked={scope === "corpus"} onChange={() => setScope("corpus")}/><span>All scripts</span></label></div></fieldset>
      <fieldset className="search-scope"><legend>Edition</legend><div className="scope-options"><label><input type="radio" name="edition" value="original" checked={edition === "original"} onChange={() => changeEdition("original")}/><span>Classic</span></label><label><input type="radio" name="edition" value="all-ages" checked={edition === "all-ages"} onChange={() => changeEdition("all-ages")}/><span>Réalta Nua</span></label></div></fieldset>
      <div className="control"><label htmlFor="search">{scope === "corpus" ? `Search all ${selectedEditionPageCount.toLocaleString() ?? ""} passages` : "Search this script"}</label><input id="search" type="search" value={scope === "corpus" ? corpusQuery : scriptQuery} onChange={event => scope === "corpus" ? setCorpusQuery(event.target.value) : setScriptQuery(event.target.value)} placeholder="English or 日本語"/></div>
      <div className="result-count" id="search-status" role="status" aria-live="polite">{resultStatus}</div>
      {edition === "original" && <label className="comparison-toggle"><input type="checkbox" checked={showMirrorMoon} onChange={event => { setShowMirrorMoon(event.target.checked); if (!event.target.checked) { setShowAuditFindings(false); setActiveFindingId(""); } }}/><span>Display mirror moon for comparison</span><small>Classic edition only</small></label>}
      {edition === "original" && showMirrorMoon && <div className="comparison-errors-row"><label className="comparison-toggle comparison-toggle-errors"><input type="checkbox" checked={showAuditFindings} onChange={event => { setShowAuditFindings(event.target.checked); setActiveFindingId(""); }}/><span>Display mirror moon errors</span></label><small className="comparison-errors-status" aria-live="polite">{showAuditFindings ? `${auditFindings.length.toLocaleString()} findings in this script` : "Source-audited notes"}</small></div>}
    </div>
    {error && <p className="script-status">{error}</p>}
    {!error && scope === "script" && data && <><div className="script-meta"><h2>{scriptTitle(data.script)}</h2><p>{data.pages.length.toLocaleString()} source passages</p></div>{visiblePages.length ? <div className="script-lines" id="script-results">{visiblePages.map(page => <ScriptLine key={page.ref} id={page.ref} page={page} showMirrorMoon={showMirrorMoon} findings={showAuditFindings ? findingsByPage.get(page.ref) ?? [] : []} activeFindingId={activeFindingId} onToggleFinding={id => setActiveFindingId(current => current === id ? "" : id)}/>)}</div> : <p className="script-empty">No passages match this search.</p>}<a className="back-to-controls" href="#reader-controls" onClick={event => { event.preventDefault(); document.getElementById("reader-controls")?.scrollIntoView({behavior:"instant", block:"start"}); document.getElementById("route")?.focus({preventScroll:true}); }}>Back to controls ↑</a></>}
    {!error && scope === "corpus" && !corpusQuery.trim() && <div className="concordance-prompt"><p className="eyebrow">All scripts</p><h2>Search every route.</h2><p>Enter Japanese or English above to search all {selectedEditionPageCount.toLocaleString()} aligned passages.</p></div>}
    {!error && scope === "corpus" && corpusQuery.trim() && concordance && <><div className="script-meta concordance-meta"><div><p className="eyebrow">All scripts</p><h2>Search results</h2></div><p>{corpusMatches.length.toLocaleString()} matches</p></div><div className="concordance-route-filter">{[["all","All sections"], ...Object.entries(routeNames)].map(([id,label]) => <button className={corpusRoute === id ? "is-active" : ""} key={id} onClick={() => setCorpusRoute(id)}>{label}<span>{id === "all" ? corpusMatches.length : editionConcordance.filter(x => x.route === id && `${x.ja}\n${x.en}`.toLocaleLowerCase().includes(corpusQuery.toLocaleLowerCase())).length}</span></button>)}</div><div className="concordance-results" id="concordance-results">{corpusMatches.slice(0,resultLimit).map(page => <CorpusResult key={`${page.scriptId}-${page.ref}`} page={page} edition={edition} showMirrorMoon={showMirrorMoon} showErrors={showAuditFindings} activeFindingId={activeFindingId} onToggleFinding={id => setActiveFindingId(current => current === id ? "" : id)}/>)}</div>{corpusMatches.length > resultLimit && <p className="script-status">Showing the first {resultLimit} matches. Refine the search to narrow the result set.</p>}</>}
  </section>;
}

function ScriptLine({id, page, showMirrorMoon, findings, activeFindingId, onToggleFinding, contextHref}: {contextHref?: string; id: string; page: Page; showMirrorMoon: boolean; findings: AuditFinding[]; activeFindingId: string; onToggleFinding: (id: string) => void}) {
  const speaker = page.speaker || (page.kind === "credit" ? "Credits" : "");
  return <article className={`script-line${showMirrorMoon ? " script-line-comparison" : ""}${findings.length ? " script-line-error" : ""}`} id={id} tabIndex={-1}><a className="line-ref" href={`#${id}`} aria-label={`Link to passage ${referenceLabel(id)}`}>{referenceLabel(id)}</a><div className="line-cell line-ja"><div className="line-cell-heading"><span className="speaker speaker-ja">{speaker}</span>{showMirrorMoon && <span className="edition-label" lang="en">Japanese</span>}</div><p lang="ja">{<JapaneseText text={page.jaRuby || page.ja || "—"}/>}</p></div><div className="line-cell line-en"><div className="line-cell-heading"><span className="speaker">{speaker}</span>{showMirrorMoon && <span className="edition-label">MAO English</span>}</div><p><EnglishText text={displayEnglish(page.en) || "—"}/></p></div>{showMirrorMoon && <div className="line-cell line-en line-todokanai"><div className="line-cell-heading"><span className="speaker">{speaker}</span><span className="edition-label">mirror moon</span></div>{findings.length ? <AuditErrorText contextHref={contextHref || `#${id}`} text={displayEnglish(page.mirrorMoon || "") || "—"} findings={findings} activeFindingId={activeFindingId} onToggleFinding={onToggleFinding}/> : <p>{displayEnglish(page.mirrorMoon || "") || "—"}</p>}</div>}</article>;
}

const comparisonScripts = new Map<string, Promise<ScriptData>>();
const comparisonAudits = new Map<string, Promise<AuditFinding[]>>();
function CorpusResult({page, edition, showMirrorMoon, showErrors, activeFindingId, onToggleFinding}: {page: ConcordancePage; edition: Edition; showMirrorMoon: boolean; showErrors: boolean; activeFindingId: string; onToggleFinding: (id: string) => void}) {
  const [mirrorMoon, setMirrorMoon] = useState(page.mirrorMoon);
  const [findings, setFindings] = useState<AuditFinding[]>([]);
  const [loadError, setLoadError] = useState("");
  const comparison = edition === "original" && showMirrorMoon;
  useEffect(() => {
    let cancelled = false;
    setFindings([]); setLoadError("");
    if (!comparison) return;
    const id = page.scriptId;
    if (!comparisonScripts.has(id)) comparisonScripts.set(id, fetch(`../data/script/${id}.json?v=${readerDataRevision}`).then(r => { if (!r.ok) throw new Error("Comparison could not be loaded."); return r.json(); }));
    comparisonScripts.get(id)!.then(data => { if (!cancelled) setMirrorMoon(data.pages.find(item => item.ref === page.ref)?.mirrorMoon); }).catch(e => { comparisonScripts.delete(id); if (!cancelled) setLoadError(String(e)); });
    if (showErrors) {
      if (!comparisonAudits.has(id)) comparisonAudits.set(id, fetch(`../data/audit/findings/${id}.json?v=${readerDataRevision}`).then(async r => { if (r.status === 404) return []; if (!r.ok) throw new Error("Audit notes could not be loaded."); const data: AuditPayload = await r.json(); if (data.schema !== "fsn-mirror-moon-editorial-errors/1") throw new Error("Unsupported audit format."); return data.findings; }));
      comparisonAudits.get(id)!.then(items => { if (!cancelled) setFindings(items.filter(item => item.ref === page.ref)); }).catch(e => { comparisonAudits.delete(id); if (!cancelled) setLoadError(String(e)); });
    }
    return () => { cancelled = true; };
  }, [page.scriptId, page.ref, comparison, showErrors]);
  const visibleFindings = comparison && showErrors ? findings : [];
  const href = `?script=${page.scriptId}&edition=${edition}${comparison ? "&compare=mirror-moon" : ""}${comparison && showErrors ? "&errors=mirror-moon" : ""}#${page.ref}`;
  return <article className={`concordance-hit${comparison ? " concordance-hit-comparison" : ""}${visibleFindings.length ? " concordance-hit-error" : ""}`}><a className="concordance-hit-link" href={href}><span>{scriptTitle(page.script)}</span><code>{referenceLabel(page.ref)}</code><strong>Open script →</strong></a><ScriptLine id={page.ref} page={{...page, mirrorMoon}} contextHref={href} showMirrorMoon={comparison} findings={visibleFindings} activeFindingId={activeFindingId} onToggleFinding={onToggleFinding}/>{loadError && <p role="status">{loadError}</p>}</article>;
}

function categoryLabel(value: string) {
  return value.split("_").filter(Boolean).map(word => word[0]?.toUpperCase() + word.slice(1)).join(" ");
}

function whitespaceInsensitiveRange(text: string, quote: string) {
  const normalizedText: string[] = [];
  const originalOffsets: number[] = [];
  let inWhitespace = false;
  for (let index = 0; index < text.length; index += 1) {
    if (/\s/u.test(text[index])) {
      if (!inWhitespace) {
        normalizedText.push(" ");
        originalOffsets.push(index);
      }
      inWhitespace = true;
    } else {
      normalizedText.push(text[index]);
      originalOffsets.push(index);
      inWhitespace = false;
    }
  }
  const needle = quote.replace(/\s+/gu, " ");
  const start = normalizedText.join("").indexOf(needle);
  if (start < 0) return null;
  const originalStart = originalOffsets[start];
  const finalNormalizedIndex = start + needle.length - 1;
  let originalEnd = originalOffsets[finalNormalizedIndex] + 1;
  if (/\s/u.test(text[originalOffsets[finalNormalizedIndex]])) {
    while (originalEnd < text.length && /\s/u.test(text[originalEnd])) originalEnd += 1;
  }
  return {start: originalStart, end: originalEnd};
}

function AuditErrorText({text, findings, activeFindingId, onToggleFinding, contextHref}: {contextHref: string; text: string; findings: AuditFinding[]; activeFindingId: string; onToggleFinding: (id: string) => void}) {
  const positioned = findings.map(finding => ({finding, range: whitespaceInsensitiveRange(text, displayEnglish(finding.highlight))})).filter((item): item is {finding: AuditFinding; range: {start: number; end: number}} => item.range !== null).sort((a, b) => a.range.start - b.range.start || b.range.end - b.range.start - (a.range.end - a.range.start));
  const fragments: ReactNode[] = [];
  const rendered = new Set<string>();
  let cursor = 0;
  for (const {finding, range: {start, end}} of positioned) {
    const highlight = text.slice(start, end);
    if (start < cursor) continue;
    if (start > cursor) fragments.push(text.slice(cursor, start));
    fragments.push(<button className="todokanai-error-trigger" type="button" key={finding.id} aria-describedby={`error-preview-${finding.id}`} aria-expanded={activeFindingId === finding.id} onClick={() => onToggleFinding(finding.id)}>{highlight}<span className="todokanai-error-preview" id={`error-preview-${finding.id}`} role="tooltip"><strong>{categoryLabel(finding.category)}</strong><span>{finding.explanation}</span></span></button>);
    rendered.add(finding.id);
    cursor = end;
  }
  if (cursor < text.length) fragments.push(text.slice(cursor));
  const unpositioned = findings.filter(finding => !rendered.has(finding.id));
  const active = findings.find(finding => finding.id === activeFindingId);
  return <><p className="todokanai-annotated-text">{fragments}</p>{unpositioned.length ? <div className="todokanai-error-fallbacks">{unpositioned.map(finding => <button type="button" key={finding.id} aria-expanded={activeFindingId === finding.id} onClick={() => onToggleFinding(finding.id)}>View {categoryLabel(finding.category).toLowerCase()} note</button>)}</div> : null}{active ? <aside className="todokanai-error-note" id={`error-note-${active.id}`} aria-label={`mirror moon error note for ${active.ref}`}><header><div><span className="todokanai-error-category">{categoryLabel(active.category)}</span><span className="todokanai-error-severity">{active.status === "confirmed_source_variant" ? "source variant" : "confirmed"}</span></div><button type="button" onClick={() => onToggleFinding(active.id)} aria-label="Close error note">Close</button></header><code>{active.id}</code><div className="todokanai-error-evidence"><span>Japanese</span><p lang="ja">{active.evidenceJa}</p></div><div className="todokanai-error-evidence"><span>mirror moon</span><p lang="en">{active.highlight}</p></div><div className="todokanai-error-evidence"><span>Governing reading</span><p>{active.governingReading}</p></div><p className="todokanai-error-explanation">{active.explanation}</p>{<div className="todokanai-error-actions"><a href={contextHref}>Open this passage in context →</a>{active.dossiers.map(id => <a href={`../audit/#dossier-${encodeURIComponent(id)}`} key={id}>Open related dossier →</a>)}</div>}</aside> : null}</>;
}
