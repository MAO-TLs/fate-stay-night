import { scriptCount, pageCount } from "../public/data/script/index.json";
import { SiteNav } from './SiteNav';
import { SiteFooter } from './SiteFooter';

const routes = [['01','Fate','fate'],['02','Unlimited Blade Works','ubw'],['03',"Heaven’s Feel",'hf']] as const;

export default function Home() {return <main>
<section className="hero"><img className="hero-backdrop" src="fate-sword-field.png" alt="" aria-hidden="true"/><SiteNav currentPage="release"/>
<div className="hero-grid shell"><div className="hero-copy"><p className="eyebrow">AN ENGLISH TRANSLATION BY MAO</p><h1>FATE/<br/><span>STAY NIGHT</span></h1>
<p className="dek">Read the source-reconciled manuscript alongside the original Japanese. The prose is available online now, before patch production and runtime testing.</p>
<div className="hero-actions"><a className="button button-primary" href="script/">Read the script <span aria-hidden="true">→</span></a></div>
<p className="compatibility">Original + Réalta Nua · Japanese + MAO English · {scriptCount.toLocaleString()} scripts</p></div><div aria-hidden="true"/></div></section>
<section className="release-strip" id="release" aria-label="Script information"><div className="shell release-grid">{[['Edition','Web script'],['Script coverage','All three routes'],['Passages',pageCount.toLocaleString()],['Status','Read online now']].map(([label,value])=><div key={label}><span className="release-label">{label}</span><strong className={label === 'Status' ? 'release-status' : undefined}>{value}</strong></div>)}</div></section>
<section className="section release-reading"><div className="shell"><div className="section-heading"><p className="eyebrow">Read online</p><h2>Three routes. One story.</h2><p>Read all three routes in Japanese and MAO English, with both the Original and Réalta Nua editions available.</p></div><div className="chapter-grid">{routes.map(([n,title,id])=><a className="chapter-card" key={id} href={'script/?section='+id}><span className="chapter-number">{n}</span><div><h3>{title}</h3><p>Available now</p></div></a>)}</div><a className="text-link" href="script/">Open the script browser <span aria-hidden="true">→</span></a></div></section>
<section className="section release-scope"><div className="shell"><div className="section-heading"><p className="eyebrow">Current scope</p><h2>The manuscript, not the patch.</h2><p>The site is for reading the English in context. It does not yet include a game patch, installation files, compatibility claims, or a comparison with previous fan translations. Those are separate publication stages.</p></div></div></section>
<section className="section release-credits"><div className="shell credits-section"><div className="section-heading"><p className="eyebrow">Credits</p><h2>MAO Translations</h2></div><dl className="credits"><div><dt>Project Lead</dt><dd>MAO</dd></div><div><dt>Translator</dt><dd>GPT-6 Astra</dd></div><div><dt>Special Thanks</dt><dd>gambs</dd></div></dl></div></section><SiteFooter/></main>}
