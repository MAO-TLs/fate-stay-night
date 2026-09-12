import { scriptCount, pageCount } from "../../public/data/script/index.json";
import { SiteNav } from '../SiteNav';
import { SiteFooter } from '../SiteFooter';
import { ScriptReader } from './ScriptReader';
export default function ScriptPage(){return <main className="reader-page mao-reader-shell"><header className="reader-header"><SiteNav currentPage="script"/><div className="shell reader-intro"><p className="eyebrow">Fate/stay night</p><h1>Script browser</h1><p>Search {pageCount.toLocaleString()} passages or read any of the {scriptCount.toLocaleString()} scripts beside the MAO English translation, including the restored H-scene versions and epilogues.</p></div></header><ScriptReader/><SiteFooter/></main>}
