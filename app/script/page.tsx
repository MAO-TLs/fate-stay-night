import { scripts } from "../../public/data/script/index.json";
import { editionParts, editionScripts } from './script-labels';
import { SiteNav } from '../SiteNav';
import { SiteFooter } from '../SiteFooter';
import { ScriptReader } from './ScriptReader';
const originalScripts = editionScripts(scripts, 'original');
const originalPassages = originalScripts.reduce((total, scene) => total + editionParts(scripts, scene.script, 'original').reduce((sceneTotal, part) => sceneTotal + (part.editionPages?.original ?? part.pages), 0), 0);
export default function ScriptPage(){return <main className="reader-page mao-reader-shell"><header className="reader-header"><SiteNav currentPage="script"/><div className="shell reader-intro"><p className="eyebrow">Fate/stay night</p><h1>Script browser</h1><p>Search {originalPassages.toLocaleString()} passages or read any of the {originalScripts.length.toLocaleString()} scripts alongside the MAO English translation, with Japanese and English available in either the Original or All-ages edition.</p></div></header><ScriptReader/><SiteFooter/></main>}
