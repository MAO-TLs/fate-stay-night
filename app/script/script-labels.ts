import supplemental from "./supplemental-scripts.json";

const digits: Record<string, number> = {一:1,二:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};
const names: Record<string, string> = {セイバー:"Saber",凛:"Rin",桜:"Sakura"};
const routeRank: Record<string, number> = {prologue:0,fate:1,ubw:2,hf:3,"last-episode":4,extras:5};
type Supplement = {layer:string;route:string;scene?:number;variant?:number;label?:string;endingOrder?:number;title?:string};
const catalog: Record<string, Supplement> = supplemental;

function details(script: string) {
  const extra = catalog[script];
  if (extra?.title) return {route:routeRank[extra.route],day:100,scene:extra.endingOrder ?? 0,variant:0,title:extra.title};
  const prologue = /^プロローグ(\d+)日目$/.exec(script);
  if (prologue) return {route:0,day:Number(prologue[1]),scene:0,variant:0,title:`Prologue, Day ${prologue[1]}`};
  const match = /^(セイバー|凛|桜)ルート([一二三四五六七八九十]+)日目-(\d+)$/.exec(script);
  if (!match) throw new Error(`Unrecognized script label: ${script}`);
  const [tens, ones] = match[2].split("十");
  const day = match[2].includes("十") ? (digits[tens] || 1) * 10 + (digits[ones] || 0) : digits[tens];
  const scene = extra?.scene ?? Number(match[3]);
  return {route:["セイバー","凛","桜"].indexOf(match[1])+1,day,scene,variant:extra?.variant ?? 0,
    title:`${names[match[1]]} Route, Day ${day} — Scene ${String(scene).padStart(2,"0")}${extra?.label ? ` (${extra.label})` : ""}`};
}

export function scriptTitle(script: string) { return details(script).title; }
export type Edition = "original" | "all-ages";
export function sceneKey(script: string) {
  if (script === "セイバールート十四日目-101") return "セイバールート十四日目-11";
  if (script === "凛ルート十四日目-130") return "凛ルート十四日目-08";
  const extra = catalog[script];
  return extra?.variant ? script.replace(/-\d+$/, "-" + String(extra.scene).padStart(2, "0")) : script;
}
export function isOriginalVariant(script: string) { return Boolean(catalog[script]?.variant); }
export function sceneTitle(script: string) { return scriptTitle(sceneKey(script)); }
export function editionParts<T extends {script:string}>(scripts:T[], script:string, edition:Edition):T[] {
  const group=scripts.filter(x => sceneKey(x.script) === sceneKey(script));
  const originals=group.filter(x => isOriginalVariant(x.script));
  const alternatives=group.filter(x => !isOriginalVariant(x.script));
  if (!originals.length) return alternatives;
  if (edition === "all-ages") return alternatives;
  return originals.sort((a,b) => Number(/-(101|130)$/.test(a.script))-Number(/-(101|130)$/.test(b.script)));
}
export function editionScripts<T extends {script:string}>(scripts:T[], edition:Edition):T[] {
  const groups = new Map<string,T[]>();
  for (const item of scripts) {
    const key=sceneKey(item.script);
    groups.set(key,[...(groups.get(key) ?? []),item]);
  }
  return [...groups.values()].map(group => editionParts(scripts,group[0].script,edition)[0] ?? group[0]).sort((a,b)=>compareScripts({script:sceneKey(a.script)},{script:sceneKey(b.script)}));
}
export function compareScripts(a: {script:string}, b: {script:string}) {
  const x=details(a.script), y=details(b.script);
  return x.route-y.route || x.day-y.day || x.scene-y.scene || x.variant-y.variant;
}
