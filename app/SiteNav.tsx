export function SiteNav({currentPage}: {currentPage: "release" | "script"}) {
 const releaseHref = currentPage === "release" ? "./" : "../";
 const scriptHref = currentPage === "script" ? "./" : "script/";
 return <nav className="nav shell" aria-label="Primary navigation">
 <a className="wordmark" href="https://mao-tls.github.io/">MAO Translations</a>
 <div className="nav-links">{([['release',releaseHref,'Home'],['script',scriptHref,'Script']] as const).map(([id,href,label])=><a key={id} href={href} aria-current={id===currentPage?'page':undefined}>{label}</a>)}<a href="https://github.com/MAO-TLs">GitHub</a></div></nav>;
}
