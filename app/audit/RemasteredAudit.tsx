"use client";

import { useEffect, useState, type ReactNode, type SyntheticEvent } from "react";
import type { Comparison } from "../script/comparison-edition";
import { SiteNav } from "../SiteNav";
import { SiteFooter } from "../SiteFooter";

type Context = {ref: string; japanese: string; english: string; scriptId: string | null; page: string | null};
type Finding = {id: string; description: string; sourceReading: string; explanation: string; contexts: Context[]; scriptId: string | null; page: string | null};
type Category = {id: string; title: string; confirmedCount: number; counterexampleCount: number; authored: boolean; exampleCount: number; citedCounterexampleCount: number};
type Payload = {schema: string; reviewedPageCount: number; totalPageCount: number; corpusConfirmedFindingCount: number; withheldBorderlineCount: number; counterexampleCount: number; dossierCount: number; citedPassageCount: number; uniqueCitedFindingCount: number; uniqueCitedCounterexampleCount: number; groups: {id: string; label: string; dossiers: Category[]}[]};
type Dossier = {claim: string; sourcePattern: string; englishEffect: string; limits: string; diagnostic: string; examples: Finding[]; counterexamples: Finding[]};
type CategoryPayload = {schema: string; id: string; dossier: Dossier | null; findings: Finding[]; counterexamples: Finding[]};
const revision = "2026-10-14-dossiers-complete";

export function TranslationSelector({selected, onChange}: {selected: Comparison; onChange: (next: Comparison) => void}) {
  return <section className="audit-selection" aria-label="Choose a translation audit">
    <div className="audit-translation-control">
      <span id="audit-translation-label">Translation</span>
      <div className="audit-translation-switch" role="group" aria-labelledby="audit-translation-label">
        <button type="button" aria-pressed={selected === "mirror-moon"} onClick={() => onChange("mirror-moon")}>mirror moon</button>
        <button type="button" aria-pressed={selected === "remastered"} onClick={() => onChange("remastered")}>REMASTERED</button>
      </div>
    </div>
    <p className="audit-translation-description">{selected === "mirror-moon"
      ? <>mirror moon is the original fan translation, completed in 2008, for the 18+ version.</>
      : <>REMASTERED is the official English translation released in 2024, based on the all-ages Réalta Nua version.</>}
    </p>
    <a className="audit-reader-link" href={`../script/?edition=${selected === "remastered" ? "all-ages" : "original"}&compare=${selected}&errors=${selected}`}>Compare in the script reader →</a>
  </section>;
}

function contextHref(context: Context) {
  return context.scriptId && context.page ? `../script/?script=${encodeURIComponent(context.scriptId)}&edition=all-ages&compare=remastered&errors=remastered#${encodeURIComponent(context.page)}` : null;
}

function Evidence({finding, category, counterexample = false}: {finding: Finding; category: string; counterexample?: boolean}) {
  const context = finding.contexts[0];
  const href = contextHref(context);
  const evidenceId = `${category}--${finding.id}`;
  return <a className={`audit-example audit-example-${counterexample ? "counterexample" : "finding"}`} id={evidenceId} href={href || `?translation=remastered&category=${encodeURIComponent(category)}#${evidenceId}`}>
    <div className="audit-example-heading"><div><span>{counterexample ? "Counterexample" : "Confirmed error"}</span></div><code>{context.ref}</code></div>
    <p lang="ja">{context.japanese}</p><p>{context.english}</p>
    {finding.contexts.slice(1).map((extra, i) => <div className="audit-support-quote" key={`${extra.ref}-${i}`}><code>{extra.ref}</code><p lang="ja">{extra.japanese}</p><p>{extra.english}</p></div>)}
    <small>{finding.explanation}</small>{href && <b>Open in script context →</b>}
  </a>;
}

function CategoryEvidence({category}: {category: Category}) {
  const [payload, setPayload] = useState<CategoryPayload | null>(null);
  const [error, setError] = useState("");
  const [requested, setRequested] = useState(false);
  const [limit, setLimit] = useState(20);
  const [counterLimit, setCounterLimit] = useState(5);
  const [showAll, setShowAll] = useState(false);
  const [targetId, setTargetId] = useState("");
  useEffect(() => {
    function syncTarget() {
      const params = new URLSearchParams(window.location.search);
      const hash = decodeURIComponent(window.location.hash.slice(1));
      if (hash === `dossier-${category.id}` || hash.startsWith(`${category.id}--`) || params.get("category") === category.id) {
        const node = document.getElementById(`dossier-${category.id}`) as HTMLDetailsElement | null;
        if (node) node.open = true;
        setRequested(true);
        setTargetId(hash.startsWith(`${category.id}--`) ? hash.slice(category.id.length + 2) : hash);
      }
    }
    syncTarget();
    window.addEventListener("hashchange", syncTarget);
    window.addEventListener("popstate", syncTarget);
    return () => {
      window.removeEventListener("hashchange", syncTarget);
      window.removeEventListener("popstate", syncTarget);
    };
  }, [category.id]);
  useEffect(() => {
    if (!requested) return;
    let cancelled = false;
    fetch(`../data/audit/remastered/categories/${category.id}.json?v=${revision}`).then(async r => {
      if (!r.ok) throw new Error("The findings could not be loaded.");
      const value = await r.json() as CategoryPayload;
      if (value.schema !== "fsn-remastered-audit-category/1" || value.id !== category.id) throw new Error("The findings could not be loaded.");
      if (!cancelled) {
        setPayload(value);
      }
    }).catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [category.id, requested]);
  useEffect(() => {
    if (!payload || !targetId) return;
    const position = payload.findings.findIndex(f => f.id === targetId);
    const counterPosition = payload.counterexamples.findIndex(f => f.id === targetId);
    if (position >= 0) setLimit(Math.max(20, position + 1));
    if (counterPosition >= 0) setCounterLimit(Math.max(5, counterPosition + 1));
    if ((position >= 0 && !payload.dossier?.examples.some(f => f.id === targetId)) ||
        (counterPosition >= 0 && !payload.dossier?.counterexamples.some(f => f.id === targetId))) setShowAll(true);
    const frame = requestAnimationFrame(() => {
      const node = document.getElementById(`${category.id}--${targetId}`) || document.getElementById(targetId);
      if (node) {
        const counters = node.closest(".audit-counterexamples");
        if (counters instanceof HTMLDetailsElement) counters.open = true;
        node.scrollIntoView({block: "start"});
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [payload, targetId, category.id]);
  function request(event: SyntheticEvent<HTMLDetailsElement>) {
    if (event.currentTarget.open) setRequested(true);
  }
  const findings = payload?.dossier && !showAll ? payload.dossier.examples : payload?.findings || [];
  const counters = payload?.dossier && !showAll ? payload.dossier.counterexamples : payload?.counterexamples || [];
  return <details className="audit-dossier" id={`dossier-${category.id}`} onToggle={request}>
    <summary><div><p className="audit-dossier-count">{category.confirmedCount.toLocaleString()} confirmed findings{category.authored ? <> · {category.exampleCount} cited passages{category.citedCounterexampleCount ? ` · ${category.citedCounterexampleCount} counterexamples` : ""}</> : ` · ${category.counterexampleCount.toLocaleString()} counterexamples`}</p><h3>{category.title}</h3></div><span className="audit-dossier-toggle"><span>Open {category.authored ? "dossier" : "category"}</span><span>Close {category.authored ? "dossier" : "category"}</span></span></summary>
    <div className="audit-dossier-body">
      {error ? <p role="status">{error}</p> : !payload ? <p role="status">Loading findings…</p> : <>
        {payload.dossier && <>
          <a className="audit-permalink" href={`#dossier-${category.id}`}>Permanent link to this dossier #</a>
          <p className="audit-dossier-claim">{payload.dossier.claim}</p>
          <dl className="audit-dossier-definition">
            <div><dt>Japanese pattern</dt><dd>{payload.dossier.sourcePattern}</dd></div>
            <div><dt>REMASTERED effect</dt><dd>{payload.dossier.englishEffect}</dd></div>
            <div><dt>Limits</dt><dd>{payload.dossier.limits}</dd></div>
          </dl>
          <p className="audit-dossier-diagnostic"><b>Corpus diagnostic</b>{payload.dossier.diagnostic}</p>
        </>}
        <div className="audit-example-list">{findings.slice(0, limit).map(finding => <Evidence finding={finding} category={category.id} key={finding.id}/>)}</div>
        {findings.length > limit && <button className="audit-show-more" type="button" onClick={() => setLimit(n => n + 20)}>Show more findings ({(findings.length - limit).toLocaleString()} remaining)</button>}
        {counters.length > 0 && payload.dossier && !showAll ? <div className="audit-example-list">{counters.map(finding => <Evidence finding={finding} category={category.id} counterexample key={finding.id}/>)}</div> : counters.length > 0 && <details className="audit-counterexamples"><summary>Counterexamples ({counters.length.toLocaleString()})</summary>
          <div className="audit-example-list">{counters.slice(0, counterLimit).map(finding => <Evidence finding={finding} category={category.id} counterexample key={finding.id}/>)}</div>
          {counters.length > counterLimit && <button className="audit-show-more" type="button" onClick={() => setCounterLimit(n => n + 20)}>Show more counterexamples</button>}
        </details>}
        {payload.dossier && <button className="audit-show-more" type="button" onClick={() => { setShowAll(v => !v); setLimit(20); setCounterLimit(5); }}>{showAll ? "Return to cited passages" : "Browse all findings in this category"}</button>}
      </>}
    </div>
  </details>;
}

export function RemasteredAudit({selector}: {selector: ReactNode}) {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    fetch(`../data/audit/remastered/index.json?v=${revision}`).then(async r => {
      if (!r.ok) throw new Error("The audit could not be loaded.");
      const value = await r.json() as Payload;
      if (value.schema !== "fsn-remastered-audit/1") throw new Error("The audit could not be loaded.");
      if (!cancelled) setPayload(value);
    }).catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, []);
  return <main className="reader-page audit-page">
    <header className="reader-header"><SiteNav currentPage="audit"/><div className="reader-intro audit-intro shell"><p className="eyebrow">Source-only editorial audit</p><h1>REMASTERED translation audit</h1><p>Every published finding was checked against the original Japanese and its surrounding context. The dossiers collect recurring problems while preserving the limits of each claim.</p></div></header>
    <div className="audit-shell shell">{selector}
      {error ? <p className="audit-empty" role="status">{error}</p> : !payload ? <p className="audit-empty" role="status">Loading audit…</p> : <>
        <section className="audit-summary" aria-labelledby="audit-summary-title"><div className="audit-summary-heading"><div><p className="eyebrow">Completed corpus review</p><h2 id="audit-summary-title">What the audit records</h2></div><p>{payload.reviewedPageCount.toLocaleString()} of {payload.totalPageCount.toLocaleString()} units reviewed</p></div>
          <div className="audit-stat-grid"><div><strong>{payload.corpusConfirmedFindingCount.toLocaleString()}</strong><span>Confirmed findings</span></div><div><strong>{payload.withheldBorderlineCount.toLocaleString()}</strong><span>Borderline calls withheld</span></div><div><strong>{payload.counterexampleCount.toLocaleString()}</strong><span>Counterexamples recorded</span></div></div>
          <p className="audit-method-note">Red markers in the script browser identify local errors. The dossiers collect recurring patterns, with explicit limits on each claim. Damaged text and edition differences are excluded.</p>
        </section>
        <section className="audit-dossiers" aria-labelledby="audit-dossiers-title"><header className="audit-dossiers-heading"><p className="eyebrow">Work-wide dossiers</p><h2 id="audit-dossiers-title">Recurring failure patterns</h2><p className="audit-method-note">Each dossier reports its category-wide finding count separately from the selected cited passages. Counts overlap because one finding may support more than one dossier.</p><p className="audit-dossiers-evidence-count">{payload.dossierCount} dossiers <span aria-hidden="true">·</span> {payload.citedPassageCount.toLocaleString()} cited passages <span aria-hidden="true">·</span> {payload.uniqueCitedFindingCount.toLocaleString()} unique findings <span aria-hidden="true">·</span> {payload.uniqueCitedCounterexampleCount.toLocaleString()} counterexamples</p></header>
          <div className="audit-group-list">{payload.groups.map(group => <details className="audit-group" key={group.id} open><summary><span>{group.label}</span><small>{group.dossiers.length} dossier{group.dossiers.length === 1 ? "" : "s"}</small></summary><div className="audit-dossier-list">{group.dossiers.map(category => <CategoryEvidence category={category} key={category.id}/>)}</div></details>)}</div>
        </section>
      </>}
    </div><SiteFooter/>
  </main>;
}
