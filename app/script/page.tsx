import { SiteNav } from '../SiteNav';
import { SiteFooter } from '../SiteFooter';
import { ScriptReader } from './ScriptReader';
export default function ScriptPage(){return <main className="reader-page mao-reader-shell"><header className="reader-header"><SiteNav currentPage="script"/><div className="shell reader-intro"><p className="eyebrow">Fate/stay night</p><h1>Script browser</h1><p>Search the complete 25,507-passage corpus or read any of its 712 scripts beside the MAO English translation.</p></div></header><ScriptReader/><SiteFooter/></main>}
