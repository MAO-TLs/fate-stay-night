export function SiteNav({currentPage}: {currentPage: "release" | "script" | "audit"}) {
 const releaseHref = currentPage === "release" ? "./" : "../";
 const scriptHref = currentPage === "script" ? "./" : currentPage === "release" ? "script/" : "../script/";
 const auditHref = currentPage === "audit" ? "./" : currentPage === "release" ? "audit/" : "../audit/";
 return <nav className="nav shell" aria-label="Primary navigation">
 <a className="wordmark" href="https://mao-tls.github.io/">MAO Translations</a>
 <div className="nav-links">{([['release',releaseHref,'Release'],['script',scriptHref,'Script'],['audit',auditHref,'Audit']] as const).map(([id,href,label])=><a key={id} href={href} aria-current={id===currentPage?'page':undefined}>{label}</a>)}<a href="https://github.com/MAO-TLs/fate-stay-night">GitHub</a></div></nav>;
}
