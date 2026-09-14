import type { Metadata } from "next";
import auditData from "../../public/data/audit/dossiers.json";
import scriptIndex from "../../public/data/script/index.json";
import { SiteFooter } from "../SiteFooter";
import { SiteNav } from "../SiteNav";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Fate/stay night mirror moon Translation Audit",
  description: "A completed source-only editorial audit of the mirror moon Fate/stay night translation.",
  alternates: { canonical: "https://mao-tls.github.io/fate-stay-night/audit/" },
};

type Example = {
  ref: string;
  findingId: string;
  japanese: string;
  mirrorMoon: string;
  note: string;
};
type Counterexample = {
  ref: string;
  script: string;
  page: string;
  japanese: string;
  mirrorMoon: string;
  whyItWorksOrLimitsClaim: string;
};
type Dossier = {
  id: string;
  title: string;
  claim: string;
  sourcePattern: string;
  mirrorMoonEffect: string;
  limits: string;
  diagnostic: string;
  confirmedCount: number;
  exampleCount: number;
  counterexampleCount: number;
  examples: Example[];
  counterexamples: Counterexample[];
};
type AuditPayload = {
  status: string;
  reviewedPageCount: number;
  corpusConfirmedFindingCount: number;
  withheldBorderlineCount: number;
  uniqueCounterexamplePageCount: number;
  dossierCount: number;
  citedPassageCount: number;
  uniqueCitedFindingCount: number;
  groups: { id: string; label: string; dossiers: Dossier[] }[];
};

const audit = auditData as AuditPayload;
const scripts = scriptIndex.scripts;

function parseRef(ref: string) {
  const pageMarker = ref.indexOf(":page");
  if (pageMarker < 0) return null;
  const page = ref.slice(pageMarker + 1).match(/^page\d+(?:-unit\d+)?/)?.[0];
  return page ? {script: ref.slice(0, pageMarker), page} : null;
}

function scriptHref(ref: string) {
  const parsed = parseRef(ref);
  if (!parsed) return "../script/";
  const script = scripts.find(item => item.script === parsed.script);
  if (!script) return "../script/";
  return `../script/?script=${encodeURIComponent(script.id)}&edition=original&compare=mirror-moon&errors=mirror-moon#${encodeURIComponent(parsed.page)}`;
}

export default function AuditPage() {
  if (audit.status !== "completed_corpus") {
    throw new Error("The mirror moon audit corpus is not ready for publication rendering.");
  }
  const renderedFindingIds = new Set<string>();

  return <main className="reader-page audit-page">
    <header className="reader-header">
      <SiteNav currentPage="audit" />
      <div className="reader-intro audit-intro shell">
        <p className="eyebrow">Source-only editorial audit</p>
        <h1>mirror moon translation audit</h1>
        <p>Every published finding was checked against the original Japanese and its surrounding context. The dossiers collect recurring problems while preserving the limits of each claim.</p>
      </div>
    </header>

    <div className="audit-shell shell">
      <section className="audit-summary" aria-labelledby="audit-summary-title">
        <div className="audit-summary-heading">
          <div><p className="eyebrow">Completed corpus review</p><h2 id="audit-summary-title">What the audit records</h2></div>
          <p>{audit.reviewedPageCount.toLocaleString()} of {audit.reviewedPageCount.toLocaleString()} aligned units reviewed</p>
        </div>
        <div className="audit-stat-grid">
          <div><strong>{audit.corpusConfirmedFindingCount.toLocaleString()}</strong><span>Confirmed findings</span></div>
          <div><strong>{audit.withheldBorderlineCount.toLocaleString()}</strong><span>Borderline calls withheld</span></div>
          <div><strong>{audit.uniqueCounterexamplePageCount.toLocaleString()}</strong><span>Counterexamples recorded</span></div>
        </div>
        <p className="audit-method-note">The audit evaluates the mirror moon English independently against the original Japanese witness. The Japanese critical edition supports interpretation; it does not replace the source. Conditional 2004 text and unresolved edition variants are withheld from the error count.</p>
      </section>

      <section className="audit-dossiers" aria-labelledby="audit-dossiers-title">
        <header className="audit-dossiers-heading">
          <p className="eyebrow">Work-wide dossiers</p>
          <h2 id="audit-dossiers-title">Recurring failure patterns</h2>
          <p className="audit-method-note">Each dossier reports its category-wide finding count separately from the selected cited passages. Counts overlap because one finding may support more than one dossier.</p>
          <p className="audit-dossiers-evidence-count">{audit.dossierCount.toLocaleString()} dossiers <span aria-hidden="true">·</span> {audit.citedPassageCount.toLocaleString()} cited passages <span aria-hidden="true">·</span> {audit.uniqueCitedFindingCount.toLocaleString()} unique findings <span aria-hidden="true">·</span> {audit.uniqueCounterexamplePageCount.toLocaleString()} counterexamples</p>
        </header>

        <div className="audit-group-list">
          {audit.groups.map(group => <details className="audit-group" key={group.id} open>
            <summary><span>{group.label}</span><small>{group.dossiers.length} dossier{group.dossiers.length === 1 ? "" : "s"}</small></summary>
            <div className="audit-dossier-list">
              {group.dossiers.map(dossier => <details className="audit-dossier" id={`dossier-${dossier.id}`} key={dossier.id}>
                <summary>
                  <div><p className="audit-dossier-count">{dossier.confirmedCount.toLocaleString()} confirmed findings · {dossier.exampleCount} cited passages{dossier.counterexampleCount ? ` · ${dossier.counterexampleCount} counterexamples` : ""}</p><h3>{dossier.title}</h3></div>
                  <span className="audit-dossier-toggle"><span>Open dossier</span><span>Close dossier</span></span>
                </summary>
                <div className="audit-dossier-body">
                  <a className="audit-permalink" href={`#dossier-${dossier.id}`}>Permanent link to this dossier #</a>
                  <p className="audit-dossier-claim">{dossier.claim}</p>
                  <dl className="audit-dossier-definition">
                    <div><dt>Japanese pattern</dt><dd>{dossier.sourcePattern}</dd></div>
                    <div><dt>mirror moon effect</dt><dd>{dossier.mirrorMoonEffect}</dd></div>
                    <div><dt>Limits</dt><dd>{dossier.limits}</dd></div>
                  </dl>
                  <p className="audit-dossier-diagnostic"><b>Corpus diagnostic</b>{dossier.diagnostic}</p>
                  <div className="audit-example-list">
                    {dossier.examples.map(example => {
                      const htmlId = renderedFindingIds.has(example.findingId) ? undefined : example.findingId;
                      renderedFindingIds.add(example.findingId);
                      return <a className="audit-example audit-example-finding" href={scriptHref(example.ref)} id={htmlId} key={`${dossier.id}-${example.findingId}`}>
                        <div className="audit-example-heading"><div><span>Confirmed error</span></div><code>{example.ref}</code></div>
                        <p lang="ja">{example.japanese}</p><p>{example.mirrorMoon}</p><small>{example.note}</small><b>Open in script context →</b>
                      </a>;
                    })}
                    {dossier.counterexamples.map(example => <a className="audit-example audit-example-counterexample" href={scriptHref(example.ref)} key={`${dossier.id}-counter-${example.ref}`}>
                      <div className="audit-example-heading"><div><span>Counterexample</span></div><code>{example.ref}</code></div>
                      <p lang="ja">{example.japanese}</p><p>{example.mirrorMoon}</p><small>{example.whyItWorksOrLimitsClaim}</small><b>Open in script context →</b>
                    </a>)}
                  </div>
                </div>
              </details>)}
            </div>
          </details>)}
        </div>
      </section>
    </div>
    <SiteFooter />
  </main>;
}
