"use client";

import { useEffect, useMemo, useState } from "react";
import { displayEnglish, displayJapanese } from "./display-text";
import { compareScripts, scriptTitle } from "./script-labels";
import { JapaneseText } from "./JapaneseText";

type ScriptMeta = {id: string; script: string; route: string; title: string; pages: number};
type Page = {ref: string; ja: string; jaRuby?: string; en: string};
type ScriptData = Omit<ScriptMeta, "pages"> & {pages: Page[]};
type IndexData = {scripts: ScriptMeta[]; scriptCount: number; pageCount: number};
type ConcordancePage = Page & {scriptId: string; script: string; route: string; title: string};
type SearchScope = "script" | "corpus";

const routeNames: Record<string, string> = {prologue: "Prologue", fate: "Fate", ubw: "Unlimited Blade Works", hf: "Heaven's Feel", "last-episode": "Last Episode"};
const resultLimit = 200;

export function ScriptReader() {
  const [index, setIndex] = useState<IndexData | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [route, setRoute] = useState("prologue");
  const [data, setData] = useState<ScriptData | null>(null);
  const [scope, setScope] = useState<SearchScope>("script");
  const [scriptQuery, setScriptQuery] = useState("");
  const [corpusQuery, setCorpusQuery] = useState("");
  const [concordance, setConcordance] = useState<ConcordancePage[] | null>(null);
  const [corpusRoute, setCorpusRoute] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("../data/script/index.json").then(r => {
      if (!r.ok) throw new Error("The script index could not be loaded.");
      return r.json();
    }).then((value: IndexData) => {
      value = {...value, scripts: [...value.scripts].sort(compareScripts)};
      setIndex(value);
      const params = new URLSearchParams(window.location.search);
      const requested = params.get("script");
      const requestedRoute = params.get("section");
      const initial = value.scripts.find(x => x.id === requested) ?? value.scripts.find(x => x.route === requestedRoute) ?? value.scripts[0];
      setSelectedId(initial.id);
      setRoute(initial.route);
    }).catch(reason => setError(String(reason)));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setData(null);
    fetch(`../data/script/${selectedId}.json`).then(r => {
      if (!r.ok) throw new Error("This script could not be loaded.");
      return r.json();
    }).then((value: ScriptData) => {
      setData(value);
      const url = new URL(window.location.href);
      url.searchParams.set("script", selectedId);
      url.searchParams.delete("section");
      window.history.replaceState({}, "", url);
    }).catch(reason => setError(String(reason)));
  }, [selectedId]);

  useEffect(() => {
    if (scope !== "corpus" || concordance) return;
    fetch("../data/script/concordance.json").then(r => r.json()).then(setConcordance).catch(reason => setError(String(reason)));
  }, [scope, concordance]);

  const routeScripts = useMemo(() => index?.scripts.filter(x => x.route === route) ?? [], [index, route]);
  const currentPosition = index?.scripts.findIndex(x => x.id === selectedId) ?? -1;
  const visiblePages = useMemo(() => {
    if (!data) return [];
    const needle = scriptQuery.trim().toLocaleLowerCase();
    return needle ? data.pages.filter(page => `${page.ja}\n${page.en}`.toLocaleLowerCase().includes(needle)) : data.pages;
  }, [data, scriptQuery]);
  const corpusMatches = useMemo(() => {
    const needle = corpusQuery.trim().toLocaleLowerCase();
    if (!needle || !concordance) return [];
    return concordance.filter(page => (corpusRoute === "all" || page.route === corpusRoute) && `${page.ja}\n${page.en}`.toLocaleLowerCase().includes(needle));
  }, [concordance, corpusQuery, corpusRoute]);

  function move(offset: number) {
    if (!index || currentPosition < 0) return;
    const next = index.scripts[currentPosition + offset];
    if (next) { setRoute(next.route); setSelectedId(next.id); setScriptQuery(""); }
  }

  const resultStatus = scope === "script"
    ? data ? `${visiblePages.length.toLocaleString()} ${scriptQuery.trim() ? "matching " : ""}passages` : "Loading script…"
    : !corpusQuery.trim() ? `${index?.pageCount.toLocaleString() ?? "…"} passages ready to search` : !concordance ? "Loading complete concordance…" : `${corpusMatches.length.toLocaleString()} matching passages`;

  return <section className="reader-shell shell compact">
    <div className="reader-controls" id="reader-controls">
      <div className="control"><label htmlFor="route">Section</label><select id="route" value={route} disabled={scope === "corpus"} onChange={event => {
        const nextRoute = event.target.value; setRoute(nextRoute);
        const first = index?.scripts.find(x => x.route === nextRoute); if (first) setSelectedId(first.id);
      }}>{Object.entries(routeNames).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></div>
      <div className="control"><label htmlFor="script">Script</label><div className="script-picker"><button onClick={() => move(-1)} disabled={scope === "corpus" || currentPosition <= 0} aria-label="Previous script">←</button><select id="script" value={selectedId} disabled={scope === "corpus"} onChange={event => setSelectedId(event.target.value)}>{routeScripts.map(item => <option key={item.id} value={item.id}>{scriptTitle(item.script)} · {item.pages.toLocaleString()} passages</option>)}</select><button onClick={() => move(1)} disabled={scope === "corpus" || !index || currentPosition >= index.scripts.length - 1} aria-label="Next script">→</button></div></div>
      <fieldset className="search-scope"><legend>Search scope</legend><div className="scope-options"><label><input type="radio" name="search-scope" checked={scope === "script"} onChange={() => setScope("script")}/><span>This script</span></label><label><input type="radio" name="search-scope" checked={scope === "corpus"} onChange={() => setScope("corpus")}/><span>All scripts</span></label></div></fieldset>
      <div className="control"><label htmlFor="search">{scope === "corpus" ? `Search all ${index?.pageCount.toLocaleString() ?? ""} passages` : "Search this script"}</label><input id="search" type="search" value={scope === "corpus" ? corpusQuery : scriptQuery} onChange={event => scope === "corpus" ? setCorpusQuery(event.target.value) : setScriptQuery(event.target.value)} placeholder="English or 日本語"/></div>
      <div className="result-count" id="search-status" role="status" aria-live="polite">{resultStatus}</div>
    </div>
    {error && <p className="script-status">{error}</p>}
    {!error && scope === "script" && data && <><div className="script-meta"><h2>{scriptTitle(data.script)}</h2><p>{data.pages.length.toLocaleString()} source passages</p></div>{visiblePages.length ? <div className="script-lines" id="script-results">{visiblePages.map(page => <ScriptLine key={page.ref} id={page.ref} page={page}/>)}</div> : <p className="script-empty">No passages match this search.</p>}<a className="back-to-controls" href="#reader-controls">Back to controls ↑</a></>}
    {!error && scope === "corpus" && !corpusQuery.trim() && <div className="concordance-prompt"><p className="eyebrow">All scripts</p><h2>Search every route.</h2><p>Enter Japanese or English above to search all {index?.pageCount.toLocaleString()} aligned passages.</p></div>}
    {!error && scope === "corpus" && corpusQuery.trim() && concordance && <><div className="script-meta concordance-meta"><div><p className="eyebrow">All scripts</p><h2>Search results</h2></div><p>{corpusMatches.length.toLocaleString()} matches</p></div><div className="concordance-route-filter">{[["all","All sections"], ...Object.entries(routeNames)].map(([id,label]) => <button className={corpusRoute === id ? "is-active" : ""} key={id} onClick={() => setCorpusRoute(id)}>{label}<span>{id === "all" ? corpusMatches.length : concordance.filter(x => x.route === id && `${x.ja}\n${x.en}`.toLocaleLowerCase().includes(corpusQuery.toLocaleLowerCase())).length}</span></button>)}</div><div className="concordance-results" id="concordance-results">{corpusMatches.slice(0,resultLimit).map(page => <article className="concordance-hit" key={`${page.scriptId}-${page.ref}`}><a className="concordance-hit-link" href={`?script=${page.scriptId}#${page.ref}`}><span>{scriptTitle(page.script)}</span><code>{page.ref}</code><strong>Open script →</strong></a><div className="concordance-hit-grid"><div className="line-cell line-ja"><span className="speaker speaker-ja">Japanese</span><p lang="ja">{<JapaneseText text={page.jaRuby || page.ja || "—"}/>}</p></div><div className="line-cell line-en"><span className="speaker">MAO English</span><p>{displayEnglish(page.en) || "—"}</p></div></div></article>)}</div>{corpusMatches.length > resultLimit && <p className="script-status">Showing the first {resultLimit} matches. Refine the search to narrow the result set.</p>}</>}
  </section>;
}

function ScriptLine({id, page}: {id: string; page: Page}) {
  return <article className="script-line" id={id} tabIndex={-1}><a className="line-ref" href={`#${id}`} aria-label={`Link to ${id}`}>{id.replace("page", "")}</a><div className="line-cell line-ja"><span className="speaker speaker-ja">Japanese</span><p lang="ja">{<JapaneseText text={page.jaRuby || page.ja || "—"}/>}</p></div><div className="line-cell line-en"><span className="speaker">MAO English</span><p>{displayEnglish(page.en) || "—"}</p></div></article>;
}
