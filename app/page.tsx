import { scripts, scriptCount, pageCount } from "../public/data/script/index.json";
import { SiteNav } from "./SiteNav";
import { SiteFooter } from "./SiteFooter";
import { InstallAnchorRelease } from "./InstallAnchorRelease";

const releaseNotesUrl = "https://github.com/MAO-TLs/fate-stay-night/releases/tag/v1.0.0";

const routes = [
  ["01", "Fate", "fate"],
  ["02", "Unlimited Blade Works", "ubw"],
  ["03", "Heaven’s Feel", "hf"],
] as const;

export default function Home() {
  return <main>
    <InstallAnchorRelease />
    <section className="hero">
      <img className="hero-backdrop" src="fate-sword-field.png" alt="" aria-hidden="true" />
      <SiteNav currentPage="release" />
      <div className="hero-grid shell">
        <div className="hero-copy">
          <p className="eyebrow">An English translation by MAO</p>
          <h1>FATE/<br /><span>STAY NIGHT</span></h1>
          <p className="dek">A new English translation of the complete visual novel, built for Réalta Nua Ultimate Edition and its Original and all-ages versions.</p>
          <div className="hero-actions">
            <a className="button button-primary" href="downloads/patch_lang_english.xp3" download>Download English patch <span aria-hidden="true">↓</span></a>
            <a className="button button-secondary" href="script/">Script <span aria-hidden="true">→</span></a>
          </div>
          <p className="compatibility">15.8 MB · <a href={releaseNotesUrl}>Release notes</a> · Version 1.0.0 · Windows · Réalta Nua Ultimate Edition required</p>
        </div>
        <div aria-hidden="true" />
      </div>
    </section>

    <section className="release-strip" id="release" aria-label="Release information">
      <div className="shell release-grid">
        {[
          ["Version", "v1.0.0"],
          ["Script coverage", "Original + all-ages"],
          ["Passages", pageCount.toLocaleString()],
          ["Status", "Complete"],
        ].map(([label, value]) => <div key={label}><span className="release-label">{label}</span><strong className={label === "Status" ? "release-status" : undefined}>{value}</strong></div>)}
      </div>
    </section>

    <section className="section shell">
      <div className="section-heading">
        <p className="eyebrow">Read online</p>
        <h2>Browse the complete script</h2>
        <p>Search {pageCount.toLocaleString()} passages or read any of the {scriptCount.toLocaleString()} scripts with the Japanese beside the MAO English translation, using either the Original or all-ages text.</p>
      </div>
      <div className="chapter-grid">
        {routes.map(([number, title, id]) => {
          const routeScripts = scripts.filter((script) => script.route === id);
          const passages = routeScripts.reduce((total, script) => total + script.pages, 0);
          return <a className="chapter-card" key={id} href={`script/?section=${id}&script=${routeScripts[0].id}`}>
          <span className="chapter-number">{number}</span>
          <div><h3>{title}</h3><p>{passages.toLocaleString()} passages · {routeScripts.length.toLocaleString()} scripts</p></div>
        </a>;
        })}
      </div>
      <a className="text-link" href="script/">Open the script browser <span aria-hidden="true">→</span></a>
    </section>

    <section className="install-section" id="install">
      <div className="section shell">
        <div className="install-heading">
          <div className="section-heading"><p className="eyebrow">Installation</p><h2>How to install the patch</h2></div>
          <p className="install-requirement">Install Réalta Nua Ultimate Edition first. This download supplies only MAO’s English language archive and does not include the game or Ultimate Edition itself.</p>
        </div>
        <ol className="install-steps">
          <li><span>01</span><div><h3>Install Ultimate Edition</h3><p>Follow the <a href="https://www.reddit.com/r/fatestaynight/comments/as1lc4/fatestay_night_realta_nua_ultimate_edition_release/">Ultimate Edition release instructions</a> with legally obtained copies of all three Réalta Nua PC routes. Keep its required <code>patch.xp3</code> and any optional feature patches you use.</p></div></li>
          <li><span>02</span><div><h3>Remove the previous English archive</h3><p>Close the game. In the Ultimate Edition game folder, remove or back up the existing <code>patch_lang_english.xp3</code>. Only one file with that name should be present.</p></div></li>
          <li><span>03</span><div><h3>Add the MAO patch</h3><p>Place the downloaded <code>patch_lang_english.xp3</code> beside <code>Fate.exe</code> and <code>patch.xp3</code>. Do not rename it.</p></div></li>
          <li><span>04</span><div><h3>Choose your edition in game</h3><p>Use Ultimate Edition’s patch settings to select the Original mature script or the all-ages Réalta Nua script. Keep the Ultimate Edition mature-content patches installed if you want their corresponding visual assets.</p></div></li>
        </ol>
        <aside className="install-warning"><strong>This is a language archive.</strong><p>It depends on the existing Ultimate Edition installation and does not replace its core patch, executable, audio, movies, or other optional packages.</p></aside>
      </div>
    </section>

    <section className="section shell credits-section">
      <div className="section-heading"><p className="eyebrow">Credits</p><h2>MAO Translations</h2></div>
      <dl className="credits">
        <div><dt>Project Lead</dt><dd>MAO</dd></div>
        <div><dt>Translator</dt><dd>GPT-6 Astra</dd></div>
        <div><dt>Special Thanks</dt><dd>gambs</dd></div>
      </dl>
    </section>
    <SiteFooter />
  </main>;
}
