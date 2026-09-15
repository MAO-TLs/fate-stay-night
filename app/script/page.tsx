import { scriptCount, pageCount } from "../../public/data/script/index.json";
import { SiteNav } from '../SiteNav';
import { SiteFooter } from '../SiteFooter';
import { ScriptReader } from './ScriptReader';
export default function ScriptPage(){return <main className="reader-page mao-reader-shell"><header className="reader-header"><SiteNav currentPage="script"/><div className="shell reader-intro"><p className="eyebrow">Script version v1.1.0</p><h1>Script browser</h1><p>Search {pageCount.toLocaleString()} passages or read any of the {scriptCount.toLocaleString()} scripts alongside the MAO English translation, with Japanese and English available in either the original or Réalta Nua edition.</p></div></header><ScriptReader/><SiteFooter/></main>}
