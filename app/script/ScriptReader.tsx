"use client";
import { referenceLabel } from "./reference-label";

import { useEffect, useMemo, useState } from "react";
import { displayEnglish, displayJapanese } from "./display-text";
import { compareScripts, sceneTitle as scriptTitle, sceneKey, isOriginalVariant, editionScripts, editionParts, type Edition } from "./script-labels";
import { JapaneseText } from "./JapaneseText";
import { editionAvailable, editionText, type EditionPassage } from "./edition-text";

type ScriptMeta = {id: string; script: string; route: string; title: string; pages: number; editionPages?: Record<Edition, number>};
type Page = EditionPassage & {ref: string; speaker?: string | null; kind?: string; mirrorMoon?: string};
type ScriptData = Omit<ScriptMeta, "pages"> & {pages: Page[]};
type IndexData = {scripts: ScriptMeta[]; scriptCount: number; pageCount: number};
type ConcordancePage = Page & {scriptId: string; script: string; route: string; title: string};
type SearchScope = "script" | "corpus";

const routeNames: Record<string, string> = {prologue: "Prologue", fate: "Fate", ubw: "Unlimited Blade Works", hf: "Heaven's Feel", "last-episode": "Last Episode", extras: "Extras"};
const resultLimit = 200;
const readerDataRevision = "2026-09-13-mirror-moon";

export function ScriptReader() {
  const [index, setIndex] = useState<IndexData | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [edition, setEdition] = useState<Edition>("original");
  const [showMirrorMoon, setShowMirrorMoon] = useState(false);
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
    if (next !== "original") setShowMirrorMoon(false);
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
      <fieldset className="search-scope"><legend>Edition</legend><div className="scope-options"><label><input type="radio" name="edition" value="original" checked={edition === "original"} onChange={() => changeEdition("original")}/><span>Original</span></label><label><input type="radio" name="edition" value="all-ages" checked={edition === "all-ages"} onChange={() => changeEdition("all-ages")}/><span>Réalta Nua</span></label></div></fieldset>
      <div className="control"><label htmlFor="search">{scope === "corpus" ? `Search all ${selectedEditionPageCount.toLocaleString() ?? ""} passages` : "Search this script"}</label><input id="search" type="search" value={scope === "corpus" ? corpusQuery : scriptQuery} onChange={event => scope === "corpus" ? setCorpusQuery(event.target.value) : setScriptQuery(event.target.value)} placeholder="English or 日本語"/></div>
      <div className="result-count" id="search-status" role="status" aria-live="polite">{resultStatus}</div>
      {edition === "original" && <label className="comparison-toggle"><input type="checkbox" checked={showMirrorMoon} onChange={event => setShowMirrorMoon(event.target.checked)}/><span>Display mirror moon for comparison</span><small>Original edition only</small></label>}
    </div>
    {error && <p className="script-status">{error}</p>}
    {!error && scope === "script" && data && <><div className="script-meta"><h2>{scriptTitle(data.script)}</h2><p>{data.pages.length.toLocaleString()} source passages</p></div>{visiblePages.length ? <div className="script-lines" id="script-results">{visiblePages.map(page => <ScriptLine key={page.ref} id={page.ref} page={page} showMirrorMoon={showMirrorMoon}/>)}</div> : <p className="script-empty">No passages match this search.</p>}<a className="back-to-controls" href="#reader-controls" onClick={event => { event.preventDefault(); document.getElementById("reader-controls")?.scrollIntoView({behavior:"instant", block:"start"}); document.getElementById("route")?.focus({preventScroll:true}); }}>Back to controls ↑</a></>}
    {!error && scope === "corpus" && !corpusQuery.trim() && <div className="concordance-prompt"><p className="eyebrow">All scripts</p><h2>Search every route.</h2><p>Enter Japanese or English above to search all {selectedEditionPageCount.toLocaleString()} aligned passages.</p></div>}
    {!error && scope === "corpus" && corpusQuery.trim() && concordance && <><div className="script-meta concordance-meta"><div><p className="eyebrow">All scripts</p><h2>Search results</h2></div><p>{corpusMatches.length.toLocaleString()} matches</p></div><div className="concordance-route-filter">{[["all","All sections"], ...Object.entries(routeNames)].map(([id,label]) => <button className={corpusRoute === id ? "is-active" : ""} key={id} onClick={() => setCorpusRoute(id)}>{label}<span>{id === "all" ? corpusMatches.length : editionConcordance.filter(x => x.route === id && `${x.ja}\n${x.en}`.toLocaleLowerCase().includes(corpusQuery.toLocaleLowerCase())).length}</span></button>)}</div><div className="concordance-results" id="concordance-results">{corpusMatches.slice(0,resultLimit).map(page => <article className="concordance-hit" key={`${page.scriptId}-${page.ref}`}><a className="concordance-hit-link" href={`?script=${page.scriptId}&edition=${edition}#${page.ref}`}><span>{scriptTitle(page.script)}</span><code>{referenceLabel(page.ref)}</code><strong>Open script →</strong></a><div className="concordance-hit-grid"><div className="line-cell line-ja"><span className="speaker speaker-ja">Japanese{page.speaker ? ` · ${page.speaker}` : page.kind === "credit" ? " · Credits" : ""}</span><p lang="ja">{<JapaneseText text={page.jaRuby || page.ja || "—"}/>}</p></div><div className="line-cell line-en"><span className="speaker">MAO English{page.speaker ? ` · ${page.speaker}` : page.kind === "credit" ? " · Credits" : ""}</span><p>{displayEnglish(page.en) || "—"}</p></div></div></article>)}</div>{corpusMatches.length > resultLimit && <p className="script-status">Showing the first {resultLimit} matches. Refine the search to narrow the result set.</p>}</>}
  </section>;
}

function ScriptLine({id, page, showMirrorMoon}: {id: string; page: Page; showMirrorMoon: boolean}) {
  const speaker = page.speaker || (page.kind === "credit" ? "Credits" : "");
  return <article className={`script-line${showMirrorMoon ? " script-line-comparison" : ""}`} id={id} tabIndex={-1}><a className="line-ref" href={`#${id}`} aria-label={`Link to passage ${referenceLabel(id)}`}>{referenceLabel(id)}</a><div className="line-cell line-ja"><div className="line-cell-heading"><span className="speaker speaker-ja">{speaker}</span>{showMirrorMoon && <span className="edition-label" lang="en">Japanese</span>}</div><p lang="ja">{<JapaneseText text={page.jaRuby || page.ja || "—"}/>}</p></div><div className="line-cell line-en"><div className="line-cell-heading"><span className="speaker">{speaker}</span>{showMirrorMoon && <span className="edition-label">MAO English</span>}</div><p>{displayEnglish(page.en) || "—"}</p></div>{showMirrorMoon && <div className="line-cell line-en line-todokanai"><div className="line-cell-heading"><span className="speaker">{speaker}</span><span className="edition-label">mirror moon</span></div><p>{displayEnglish(page.mirrorMoon || "") || "—"}</p></div>}</article>;
}
