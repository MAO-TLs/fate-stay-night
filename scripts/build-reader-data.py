from __future__ import annotations

from pathlib import Path
import json
import hashlib
import re

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
JP = ROOT / "source/reader/jp/base"
EN = ROOT / "campaign/reconciliation/by_script"
SCENE_INDEX = ROOT / "source/reader/scene-index.js"
OUT = SITE / "public/data/script"


def english_pages(path: Path) -> list[tuple[str, str]]:
    pages: list[tuple[str, list[str]]] = []
    in_page = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^#{2,4}\s+(page\d+)\s*$", raw)
        if match:
            pages.append((match.group(1), []))
            in_page = True
        elif re.match(r"^#{1,6}\s", raw):
            in_page = False
        elif pages and in_page:
            pages[-1][1].append(raw)
    cleaned = []
    for label, lines in pages:
        text = "\n".join(lines).strip()
        if re.fullmatch(r"\*?\[(?:No|no) (?:translatable|reader-facing|spoken|active)[^\]]*\]\*?", text):
            text = ""
        cleaned.append((label, text))
    return cleaned


def japanese_pages(path: Path, preserve_ruby: bool = False) -> list[tuple[str, str]]:
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
                text = raw.replace("[auml]", "ä").replace("[szlig]", "ß")
                if not preserve_ruby:
                    text = re.sub(r"\[ruby\s+text=([^\]]+)\]", "", text)
                text = re.sub(r"\[(?:lr|r|line\d+|font[^\]]*|resetfont|ch[^\]]*)\]", "\n", text)
                text = re.sub(r"\[(?!ruby\s)[^\]]+\]", "", text)
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


def publication_inventory():
    catalog = json.loads((SITE / "app/script/supplemental-scripts.json").read_text())
    ordered = [name for name in scene_order() if (JP / f"{name}.ks").exists()]
    if len(set(ordered)) != len(ordered) or set(ordered) != {p.stem for p in JP.glob("*.ks")}:
        raise RuntimeError("Scene index must cover every base source script exactly once.")
    ordered += [n for n in catalog if n not in ordered]
    result = []
    for name in ordered:
        meta = catalog.get(name, {})
        layer = meta.get("layer", "base")
        source = (ROOT / "source/reader/supplemental/jp/base" if layer == "supplemental"
                  else ROOT / "source/reader/jp" / layer) / f"{name}.ks"
        manuscript = EN / f"{name}.md"
        if not source.exists() or not manuscript.exists():
            raise RuntimeError(f"Missing source or manuscript: {name}")
        if layer == "supplemental":
            manifest = json.loads((ROOT / "campaign/supplemental_epilogues_v1/second-pass-checkpoint.json").read_text())
            bound = next(x for x in manifest["manuscripts"] if x["script"] == name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != bound["source_sha256"] or hashlib.sha256(manuscript.read_bytes()).hexdigest() != bound["final_sha256"]:
                raise RuntimeError(f"Supplement differs from reviewed checkpoint: {name}")
        result.append((name, meta.get("route", route_for(name)), source, manuscript))
    return result


def stable_ids(names, published):
    ids = {item["script"]: item["id"] for item in published}
    if len(ids) != len(published) or len(set(ids.values())) != len(ids):
        raise RuntimeError("Duplicate published script or ID.")
    omitted = set(ids) - set(names)
    if omitted:
        raise RuntimeError(f"Refusing to remove {len(omitted)} published scripts. No files were changed.")
    next_id = max((int(i) for i in ids.values()), default=-1) + 1
    for name in names:
        if name not in ids:
            ids[name] = f"{next_id:04d}"
            next_id += 1
    return ids


def main() -> None:
    inventory = publication_inventory()
    index_path = OUT / "index.json"
    published = json.loads(index_path.read_text())["scripts"] if index_path.exists() else []
    ids = stable_ids([n for n, _, _, _ in inventory], published)
    payloads = []
    concordance = []
    # Validate the entire projection before writing any published file.
    for script, route, jp_path, en_path in inventory:
        jp_pages = japanese_pages(jp_path)
        ruby_pages = japanese_pages(jp_path, preserve_ruby=True)
        en_pages = english_pages(en_path)
        if [x[0] for x in jp_pages] != [x[0] for x in en_pages]:
            raise RuntimeError(f"Page mismatch: {script}")
        payload = {
            "id": ids[script], "script": script, "route": route, "title": script,
            "pages": [
                {"ref": label, "ja": japanese, "jaRuby": ruby, "en": english}
                for (label, japanese), (_, ruby), (_, english) in zip(jp_pages, ruby_pages, en_pages)
            ],
        }
        payloads.append(payload)
        concordance.extend({"scriptId": ids[script], "script": script, "route": route, "title": script, **page} for page in payload["pages"])
    scripts = [{**{k:p[k] for k in ("id", "script", "route", "title")}, "pages":len(p["pages"])} for p in payloads]
    index = {"scripts": scripts, "scriptCount": len(scripts), "pageCount": sum(x["pages"] for x in scripts)}
    OUT.mkdir(parents=True, exist_ok=True)
    for payload in payloads:
        (OUT / f'{payload["id"]}.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "concordance.json").write_text(json.dumps(concordance, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"scripts": index["scriptCount"], "pages": index["pageCount"], "preserved_ids":len(published)}))


if __name__ == "__main__":
    main()
