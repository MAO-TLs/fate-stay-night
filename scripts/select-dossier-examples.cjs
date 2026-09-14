// Choose readable evidence with broad coverage; this does not change verdicts.
const routeOf = f => f.script.startsWith('プロローグ') ? 'prologue'
  : f.script.startsWith('セイバー') ? 'fate'
  : f.script.startsWith('凛') ? 'ubw'
  : f.script.startsWith('桜') ? 'hf' : 'extras';
const evidenceKey = f => `${f.evidenceJa}\n${f.highlight}`.replace(/\s+/g, '').toLowerCase();
// Narrow thematic dossiers to evidence that explicitly identifies their topic.
// Do not use route names as character evidence: a route contains many speakers.
const themes = {
  rin: /\bRin\b|Tohsaka|遠坂|凛/i,
  ayako: /Ayako|Mitsuzuri|綾子|美綴/i,
  shinji: /Shinji|慎二/i,
  taiga: /Taiga|Fujimura|藤村|大河/i,
  issei: /Issei|柳洞|一成/i,
  emiya: /breakfast|household|kitchen|朝食|台所/i,
  shirou: /Shirou|Shiro\b|士郎/i,
  saber: /Saber|セイバー/i,
  assassin: /Assassin|Kojir|アサシン|小次郎/i,
  illya: /Illya|Ilya|イリヤ/i,
  rider: /Rider|ライダー/i,
  kotomine: /Kotomine|Kirei|言峰|綺礼/i,
  caster: /Caster|キャスター/i,
  kuzuki: /Kuzuki|葛木/i,
  gilgamesh: /Gilgamesh|ギルガメッシュ/i,
  lancer: /Lancer|ランサー/i,
  zouken: /Zouken|Zoken|臓硯/i,
  sakura: /Sakura|桜/i,
  summoner: /summon|Master|Servant|マスター|サーヴァント|召喚/i,
  archer: /Archer|アーチャー/i,
  magecraft: /magecraft|sorcery|magic|魔術|魔法/i,
  magical: /circuit|organ|nerve|self.erasure|身体|肉体|内臓|神経|魔術回路/i,
  command: /command spell|command seal|令呪/i,
  fuyuki: /Fuyuki|leyline|leylines|land|冬木|霊脈|土地/i,
  servant: /Servant|class|detect|presence|サーヴァント|気配|クラス/i,
};
const focusedThemes = {
  'shirou-fire-survival-and-dead-heart': /fire|surviv|trauma|dead|death|救|災|死|心/i,
  'shirou-justice-ideal-and-childhood-conduct': /justice|ideal|hero|child|正義|理想|子供/i,
  'rin-archer-domestic-trust-and-address': /Archer|アーチャー|trust|信頼/i,
  'archer-reveal-memory-and-mutual-recognition': /memor|recogn|identit|future|past|記憶|未来|過去|正体/i,
  'shirou-sakura-reciprocal-morning-care': /morning|breakfast|meal|plate|bowl|cook|朝|皿|茶碗|料理/i,
};
const topicMatch = (f, dossierId) => {
  const pattern = focusedThemes[dossierId] || themes[dossierId.split('-')[0]];
  return !pattern || pattern.test(`${f.evidenceJa}\n${f.highlight}\n${f.explanation}`);
};
function clarity(f) {
  let score = 0;
  if (f.evidenceJa.length >= 8 && f.evidenceJa.length <= 220) score += 3;
  if (f.highlight.length >= 15 && f.highlight.length <= 300) score += 3;
  if (f.explanation.length >= 40 && f.explanation.length <= 450) score += 2;
  if (/negat|opposite|revers|subject|object|instead|rather than|changes|turns|mistranslat|incorrect/i.test(f.explanation)) score += 2;
  if (/may |might |possibly|arguably|could |weakens|flattens|tenderness|heightened/i.test(f.explanation)) score -= 4;
  if (/\[(?:ruby|line|font)|@\w/.test(f.evidenceJa + f.highlight)) score -= 3;
  return score;
}
function selectExamples(candidates, limit = 8, dossierId = '') {
  const valid = candidates.filter(f => f && f.script && f.evidenceJa && f.highlight && f.explanation);
  const relevant = valid.filter(f => topicMatch(f, dossierId));
  const pool = new Set(relevant.map(evidenceKey)).size >= limit ? relevant : valid;
  const selected = [], routes = new Map(), scripts = new Set(), pages = new Set(), evidence = new Set();
  while (selected.length < limit) {
    const eligible = pool.filter(f => !selected.some(s => s.id === f.id) && !evidence.has(evidenceKey(f)));
    if (!eligible.length) break;
    const score = f => (topicMatch(f, dossierId) ? 200 : 0)
      + (!routes.has(routeOf(f)) ? 100 : 0)
      + (!scripts.has(f.script) ? 40 : 0)
      + (!pages.has(`${f.script}:${f.ref}`) ? 20 : 0)
      - (routes.get(routeOf(f)) || 0) * 6 + clarity(f);
    eligible.sort((a,b) => score(b) - score(a) || a.id.localeCompare(b.id));
    const f = eligible[0];
    selected.push(f);
    routes.set(routeOf(f), (routes.get(routeOf(f)) || 0) + 1);
    scripts.add(f.script); pages.add(`${f.script}:${f.ref}`); evidence.add(evidenceKey(f));
  }
  return selected;
}
module.exports = {selectExamples, routeOf, evidenceKey, topicMatch};
