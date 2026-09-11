const digits: Record<string, number> = {一:1,二:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};
const names: Record<string, string> = {セイバー:"Saber",凛:"Rin",桜:"Sakura"};

function details(script: string) {
  const prologue = /^プロローグ(\d+)日目$/.exec(script);
  if (prologue) return {route:0, day:Number(prologue[1]), scene:0, title:`Prologue, Day ${prologue[1]}`};
  const match = /^(セイバー|凛|桜)ルート([一二三四五六七八九十]+)日目-(\d+)$/.exec(script);
  if (!match) throw new Error(`Unrecognized script label: ${script}`);
  const [tens, ones] = match[2].split("十");
  const day = match[2].includes("十") ? (digits[tens] || 1) * 10 + (digits[ones] || 0) : digits[tens];
  return {route:["セイバー","凛","桜"].indexOf(match[1])+1, day, scene:Number(match[3]),
    title:`${names[match[1]]} Route, Day ${day} — Scene ${match[3].padStart(2,"0")}`};
}

export function scriptTitle(script: string) { return details(script).title; }
export function compareScripts(a: {script:string}, b: {script:string}) {
  const x=details(a.script), y=details(b.script);
  return x.route-y.route || x.day-y.day || x.scene-y.scene;
}
