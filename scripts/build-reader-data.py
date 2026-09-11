from __future__ import annotations

from pathlib import Path
import json
import re

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
JP = ROOT / "source/reader/jp/base"
EN = ROOT / "campaign/reconciliation/by_script"
SCENE_INDEX = ROOT / "source/reader/scene-index.js"
OUT = SITE / "public/data/script"


def english_pages(path: Path) -> list[tuple[str, str]]:
    pages: list[tuple[str, list[str]]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^#{2,4}\s+(page\d+)\s*$", raw)
        if match:
            pages.append((match.group(1), []))
        elif pages and not raw.startswith("#"):
            pages[-1][1].append(raw)
    cleaned = []
    for label, lines in pages:
        text = "\n".join(lines).strip()
        if re.fullmatch(r"\*?\[(?:No|no) (?:translatable|reader-facing|spoken|active)[^\]]*\]\*?", text):
            text = ""
        cleaned.append((label, text))
    return cleaned


def japanese_pages(path: Path) -> list[tuple[str, str]]:
    pages: list[tuple[str, list[str]]] = []
    in_comment = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw.strip()
        if stripped.startswith("/*"):
            in_comment = True
        if not in_comment:
            match = re.match(r"^\*(page\d+)(?:\||$)", raw)
            if match:
                pages.append((match.group(1), []))
            elif pages and raw and not raw.startswith(("@", "*", ";")):
                text = raw
                text = re.sub(r"\[ruby\s+text=([^\]]+)\]", "", text)
                text = re.sub(r"\[(?:lr|r|line\d+|font[^\]]*|resetfont|ch[^\]]*)\]", "\n", text)
                text = re.sub(r"\[[^\]]+\]", "", text)
                text = text.replace("　", " ").strip()
                if text:
                    pages[-1][1].append(text)
        if stripped.endswith("*/"):
            in_comment = False
    return [(label, "\n".join(lines).strip()) for label, lines in pages]


def route_for(script: str) -> str:
    if script.startswith("プロローグ"):
        return "prologue"
    if script.startswith("セイバー"):
        return "fate"
    if script.startswith("凛"):
        return "ubw"
    return "hf"


def scene_order() -> list[str]:
    source = SCENE_INDEX.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "source/reader/manifest.json").read_text(encoding="utf-8"))
    section_source = source.split("export const sections =", 1)[1]
    scene_ids = [json.loads('"' + value + '"') for value in re.findall(r'id:\s*"((?:\\.|[^"])*)"', section_source)]
    return [manifest["scene_mapping"][scene_id] for scene_id in scene_ids if manifest["scene_mapping"].get(scene_id)]


def natural_key(script: str):
    route_rank = {"prologue": 0, "fate": 1, "ubw": 2, "hf": 3}[route_for(script)]
    number = re.search(r"-(\d+)$", script)
    return route_rank, script.replace(number.group(0), "") if number else script, int(number.group(1)) if number else 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scripts = []
    concordance = []
    ordered_scripts = [script for script in scene_order() if (JP / f"{script}.ks").exists() and (EN / f"{script}.md").exists()]
    if len(ordered_scripts) != 712 or len(set(ordered_scripts)) != 712:
        raise RuntimeError(f"Scene index does not resolve to 712 unique base scripts: {len(ordered_scripts)} / {len(set(ordered_scripts))}")
    for position, script in enumerate(ordered_scripts):
        jp_path = JP / f"{script}.ks"
        en_path = EN / f"{script}.md"
        jp_pages = japanese_pages(jp_path)
        en_pages = english_pages(en_path)
        if [x[0] for x in jp_pages] != [x[0] for x in en_pages]:
            raise RuntimeError(f"Page mismatch: {script}")
        item_id = f"{position:04d}"
        route = route_for(script)
        payload = {
            "id": item_id,
            "script": script,
            "route": route,
            "title": script,
            "pages": [
                {"ref": label, "ja": japanese, "en": english}
                for (label, japanese), (_, english) in zip(jp_pages, en_pages)
            ],
        }
        (OUT / f"{item_id}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        scripts.append({"id": item_id, "script": script, "route": route, "title": payload["title"], "pages": len(payload["pages"])})
        concordance.extend({"scriptId": item_id, "script": script, "route": route, "title": payload["title"], **page} for page in payload["pages"])
    index = {"scripts": scripts, "scriptCount": len(scripts), "pageCount": sum(x["pages"] for x in scripts)}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "concordance.json").write_text(json.dumps(concordance, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"scripts": index["scriptCount"], "pages": index["pageCount"]}))


if __name__ == "__main__":
    main()
