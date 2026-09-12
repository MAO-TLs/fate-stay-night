from __future__ import annotations

from pathlib import Path
import json
import hashlib
import re
import argparse

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
JP = ROOT / "source/reader/jp/base"
EN = ROOT / "campaign/reconciliation/by_script"
MM = ROOT / "source/reader/eng/base"
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


def japanese_pages(path: Path, preserve_ruby: bool = False, restored_lines=None, omitted_lines=None) -> list[tuple[str, str]]:
    pages: list[tuple[str, list[str]]] = []
    in_comment = False
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if omitted_lines and line_number in omitted_lines:
            continue
        if restored_lines and line_number in restored_lines:
            if not raw.startswith(";"):
                raise RuntimeError(f"Restoration is not a commented source line: {path}:{line_number}")
            raw = raw[1:]
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


def comparator_pages(path: Path) -> list[tuple[str, str]]:
    """Extract the archived mirror moon reader witness by engine page."""
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
            elif pages:
                align = re.match(r'^@align\b.*?\btext="([^"]*)"', stripped)
                if align:
                    pages[-1][1].append(align.group(1))
                elif raw and not raw.startswith(("@", "*", ";")):
                    pages[-1][1].append(raw)
        if stripped.endswith("*/"):
            in_comment = False
    cleaned = []
    for label, lines in pages:
        text = "\n".join(lines).replace("[auml]", "ä").replace("[szlig]", "ß")
        text = re.sub(r"\[(?:lr|l|r|line\d+|font[^\]]*|resetfont|ch[^\]]*|indent|endindent)\]", "\n", text)
        text = re.sub(r"\[[^\]]+\]", "", text)
        cleaned.append((label, "\n".join(line.strip() for line in text.splitlines() if line.strip())))
    return cleaned


def restored_source_text(source_lines, preserve_ruby: bool = False) -> str:
    """Project explicitly bound commented prose without relying on active page labels."""
    text = "\n".join(line["raw"][1:] for line in source_lines)
    text = text.replace("[auml]", "ä").replace("[szlig]", "ß")
    if not preserve_ruby:
        text = re.sub(r"\[ruby\s+text=([^\]]+)\]", "", text)
    text = re.sub(r"\[(?:lr|l|r|line\d+|font[^\]]*|resetfont|ch[^\]]*)\]", "\n", text)
    text = re.sub(r"\[(?!ruby\s)[^\]]+\]", "", text)
    return "\n".join(line.replace("　", " ").strip() for line in text.splitlines() if line.strip())


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
            checkpoint = meta.get("checkpoint", "supplemental_epilogues_v1")
            manifest = json.loads((ROOT / "campaign" / checkpoint / "second-pass-checkpoint.json").read_text())
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


def fragment_editions(script, pages):
    if not script.startswith("セイバー"):
        return
    folder = ROOT / "campaign/commented_source_restoration_v1/partial_page_variants"
    # These reviewed records contain additions only: no else-branch replacement
    # or ambiguous engine-run grouping. Restore only their bound comment lines.
    stems = ["saber1-01-page14", "saber1-01-page19",
             "saber1-02-page10", "saber1-02-page11", "saber1-02-page18",
             "saber1-06-page7", "saber1-06-page11", "saber1-06-page41",
             "saber1-14-page7", "saber1-14-page8",
             "saber1-07-page0", "saber1-07-page1", "saber4-04-page21", "saber4-04-page22",
             "saber14-00-page4", "saber14-00-page90", "saber14-00-page22", "saber14-00-page40"]
    reader_refs = {"saber1-07-page1": "page0", "saber4-04-page22": "page21"}
    pending = {}
    for stem in stems:
        path = folder / f"{stem}.composite.json"
        record = json.loads(path.read_text())
        if record["entry"] != script + ".ks":
            continue
        binding = json.loads((folder / f"{stem}.binding.json").read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != binding["second_pass_sha256"]:
            raise RuntimeError(f"Fragment review changed: {stem}")
        counts, paths = binding["paragraph_counts"], binding["target_text_paths"]
        collapsed_runs = {
            "saber14-00-page22": ("d9963e3323ac1ed895132158cf0c7344f1b4fdaa4051f807bb379e2b4def25c2", [2, 2]),
            "saber14-00-page40": ("90dd901413a55f408aebec92e1a223c4c2cb5f8576f73b652f8546f22b3214b7", [3, 2]),
        }
        if stem in collapsed_runs:
            expected, counts = collapsed_runs[stem]
            if binding["second_pass_sha256"] != expected:
                raise RuntimeError(f"Shared run grouping needs review: {stem}")
        if len(counts) != len(paths) or sum(counts) != len(record["english"].strip().split("\n\n")):
            raise RuntimeError(f"Ambiguous fragment composition: {stem}")
        for conditions in paths:
            for kind, expression, branch in conditions:
                if kind != "if" or branch != 0 or expression not in (
                    'exp="sf.gmature"', 'exp="sf.gtext==\'classic\'"', 'exp="sf.gtext!=\'realta\'"'
                ):
                    raise RuntimeError(f"Fragment is not an Original-only addition: {stem}")
        source = ROOT / record["source_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
            raise RuntimeError(f"Fragment source changed: {stem}")
        lines = source.read_text(encoding="utf-8-sig").splitlines()
        for line in record["source_lines"]:
            if lines[line["line"] - 1] != line["raw"] or (not line["raw"].startswith(";") and stem != "saber1-07-page1"):
                raise RuntimeError(f"Fragment source line mismatch: {stem}")
        restored = {line["line"] for line in record["source_lines"] if line["raw"].startswith(";")}
        ref = reader_refs.get(stem, record["target_ref"])
        for line_number in (line["line"] for line in record["source_lines"]):
            source_ref = next((re.match(r"\*(page\d+)", line)[1] for line in reversed(lines[:line_number]) if re.match(r"\*(page\d+)", line)), None)
            if source_ref != ref:
                raise RuntimeError(f"Fragment crosses reader page boundaries: {stem}")
        group = pending.setdefault(ref, {"source": source, "restored": set(), "english": []})
        if group["source"] != source:
            raise RuntimeError(f"Fragment source differs within reader page: {stem}")
        group["restored"].update(restored)
        group["english"].append(record["english"].strip())
    for ref, group in pending.items():
        source, restored = group["source"], group["restored"]
        page = next(p for p in pages if p["ref"] == ref)
        page["editions"] = {
            "all-ages": {key: page[key] for key in ("ja", "jaRuby", "en")},
            "original": {
                "ja": dict(japanese_pages(source, restored_lines=restored))[ref],
                "jaRuby": dict(japanese_pages(source, preserve_ruby=True, restored_lines=restored))[ref],
                "en": "\n\n".join(group["english"]),
            },
        }


def restored_page_editions(script, pages):
    folder = ROOT / "campaign/commented_source_restoration_v1"
    for path in sorted(folder.glob("*.second-pass.json")):
        record = json.loads(path.read_text())
        if record["entry"] != script + ".ks":
            continue
        binding = json.loads(path.with_name(path.name.replace("second-pass", "binding")).read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != binding["second_pass_sha256"]:
            raise RuntimeError(f"Restored page review changed: {path.name}")
        for conditions in binding["target_text_paths"]:
            for kind, expression, branch in conditions:
                if kind != "if" or branch != 0 or expression not in (
                    'exp="sf.ghentai"', 'exp="sf.gmature"',
                    'exp="sf.gtext==\'classic\'"', 'exp="sf.gtext!=\'realta\'"'
                ):
                    raise RuntimeError(f"Unexpected restored page edition: {path.name}")
        source = ROOT / record["source_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
            raise RuntimeError(f"Restored page source changed: {path.name}")
        lines = source.read_text(encoding="utf-8-sig").splitlines()
        for line in record["source_lines"]:
            if lines[line["line"] - 1] != line["raw"] or not line["raw"].startswith(";"):
                raise RuntimeError(f"Restored page source line changed: {path.name}")
        ref = record["target_ref"]
        restored = {line["line"] for line in record["source_lines"]}
        for number in restored:
            source_ref = next((re.match(r"\*(page\d+)", line)[1] for line in reversed(lines[:number]) if re.match(r"\*(page\d+)", line)), None)
            if source_ref != ref:
                raise RuntimeError(f"Restored page needs reader alignment: {path.name}")
        page = next(p for p in pages if p["ref"] == ref)
        if page["ja"].strip() or page["en"].strip():
            raise RuntimeError(f"Restoration would replace shared prose: {path.name}")
        page["editions"] = {
            "all-ages": {key: page[key] for key in ("ja", "jaRuby", "en")},
            "original": {
                "ja": dict(japanese_pages(source, restored_lines=restored))[ref],
                "jaRuby": dict(japanese_pages(source, preserve_ruby=True, restored_lines=restored))[ref],
                "en": record["english"],
            },
        }


def embedded_editions(script, pages, manuscript):
    # Editions-only refreshes read their previous output. Remove generated
    # edition-only pages before rebuilding them so this overlay is idempotent.
    pages[:] = [page for page in pages if not page.get("editionVirtual")]
    restored_page_editions(script, pages)
    fragment_editions(script, pages)
    additions = json.loads((SITE / "app/script/edition-additions.json").read_text())
    for addition in additions:
        if addition["script"] != script:
            continue
        source = JP / (script + ".ks")
        if hashlib.sha256(source.read_bytes()).hexdigest() != addition["source_sha256"]:
            raise RuntimeError(f"New edition source changed: {script}")
        lines = source.read_text(encoding="utf-8-sig").splitlines()
        for line in addition["source_lines"]:
            if lines[line["line"] - 1] != line["raw"]:
                raise RuntimeError(f"New edition source line changed: {script}")
        for line in addition.get("omitted_source_lines", []):
            if lines[line["line"] - 1] != line["raw"]:
                raise RuntimeError(f"Edition replacement source changed: {script}")
        if addition.get("virtual"):
            if any(page["ref"] == addition["ref"] for page in pages):
                raise RuntimeError(f"Edition-only page collides with shared page: {script} {addition['ref']}")
            page = {
                "ref": addition["ref"], "ja": "", "jaRuby": "", "en": "",
                "editionVirtual": True, "availableEditions": ["original"],
                "editions": {"original": {
                    "ja": restored_source_text(addition["source_lines"]),
                    "jaRuby": restored_source_text(addition["source_lines"], preserve_ruby=True),
                    "en": addition["english"],
                }},
            }
            pages.append(page)
            pages.sort(key=lambda item: int(re.search(r"\d+", item["ref"]).group()))
            continue
        page = next(p for p in pages if p["ref"] == addition["ref"])
        shared = page["en"].split("\n\n")
        position = addition["insert_after_paragraph"]
        replaced = addition.get("replace_paragraphs", 0)
        if not 0 <= position <= len(shared) or not 0 <= replaced <= len(shared) - position:
            raise RuntimeError(f"Invalid edition insertion point: {script}")
        restored = {line["line"] for line in addition["source_lines"]}
        omitted = {line["line"] for line in addition.get("omitted_source_lines", [])}
        if "existing_english" in addition:
            # Some published pages already translated the commented Original
            # sentence. Keep that English verbatim; do not insert it twice.
            existing = addition["existing_english"]
            if not existing or shared[position:position + len(existing)] != existing:
                raise RuntimeError(f"Existing edition English changed: {script} {page['ref']}")
            if replaced or omitted:
                raise RuntimeError(f"Conflicting existing-English alignment: {script}")
            page["editions"] = {
                "all-ages": {
                    "ja": page["ja"], "jaRuby": page["jaRuby"],
                    "en": "\n\n".join(shared[:position] + addition.get("all_ages_replacement", []) + shared[position + len(existing):]),
                },
                "original": {
                    "ja": dict(japanese_pages(source, restored_lines=restored))[page["ref"]],
                    "jaRuby": dict(japanese_pages(source, preserve_ruby=True, restored_lines=restored))[page["ref"]],
                    "en": page["en"],
                },
            }
            continue
        if "reuse" in addition:
            reuse = addition["reuse"]
            donor = next(a for a in additions if a["script"] == reuse["script"] and a["ref"] == reuse["ref"])
            count = reuse["paragraphs"]
            if [x["raw"] for x in addition["source_lines"][:count]] != [x["raw"] for x in donor["source_lines"][:count]]:
                raise RuntimeError(f"Reused edition text has different Japanese: {script}")
            english = "\n\n".join(donor["english"].split("\n\n")[:count] + [addition["transition"]])
        else:
            english = addition["english"]
        page["editions"] = {
            "all-ages": {key: page[key] for key in ("ja", "jaRuby", "en")},
            "original": {
                "ja": dict(japanese_pages(source, restored_lines=restored, omitted_lines=omitted))[page["ref"]],
                "jaRuby": dict(japanese_pages(source, preserve_ruby=True, restored_lines=restored, omitted_lines=omitted))[page["ref"]],
                "en": "\n\n".join(shared[:position] + [english] + shared[position + replaced:]),
            },
        }
    # These two complete-page alternatives have reviewed dual-source bindings.
    # Do not mistake engine-order composite files for linear reader prose.
    if script != "桜ルート七日目-18":
        return
    for ordinal in (0, 8, 11, 12, 13, 14, 15):
        stem = f"hf7-18-page{ordinal}.dual-source"
        folder = ROOT / "campaign/commented_source_restoration_v1/partial_page_variants"
        composite_path = folder / f"{stem}-composite.json"
        binding = json.loads((folder / f"{stem}-binding.json").read_text())
        if hashlib.sha256(composite_path.read_bytes()).hexdigest() != binding["second_pass_sha256"]:
            raise RuntimeError(f"Edition composite changed: {stem}")
        composite = json.loads(composite_path.read_text())
        composition = composite["composition"]
        if hashlib.sha256(manuscript.read_bytes()).hexdigest() != composition["canonical_sha256"]:
            raise RuntimeError(f"Edition canonical manuscript changed: {stem}")
        witness = composite["additional_sources"][0]
        source = ROOT / witness["source_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != witness["source_sha256"]:
            raise RuntimeError(f"Edition witness changed: {stem}")
        lines = source.read_text(encoding="utf-8-sig").splitlines()
        for line in witness["source_lines"]:
            if lines[line["line"] - 1] != line["raw"]:
                raise RuntimeError(f"Edition witness line changed: {stem}")
        counts, paths = binding["paragraph_counts"], binding["target_text_paths"]
        paragraphs = composite["english"].split("\n\n")
        if ordinal == 13:
            # The binding combines two adjacent unconditional runs. The source
            # has shared silence/light narration, then insects vs. monsters.
            if binding["second_pass_sha256"] != "33d928d1a06dcf3b6c8054542d63e26c2d5d184eda22725dd25ed6c5bc9d90db":
                raise RuntimeError("Page13 composition requires a fresh review")
            counts = [3, 2, 2]
        elif ordinal == 15:
            # Two dialogue paragraphs share the first engine run. The final
            # sentence is split only to select insects or monsters, not prose.
            if binding["second_pass_sha256"] != "60e7aeb198f7cca3ae86818d9a1d70f15fd3dd6a98f13070d712661ed22dc9d1":
                raise RuntimeError("Page15 composition requires a fresh review")
            counts = [2, 1, 1, 1]
        if len(counts) != len(paths) or sum(counts) != len(paragraphs):
            raise RuntimeError(f"Ambiguous edition composition: {stem}")
        original, offset = [], 0
        for count, conditions in zip(counts, paths):
            visible = True
            for kind, expression, branch in conditions:
                if kind != "if" or expression != 'exp="sf.gmature"' or branch not in (0, 1):
                    raise RuntimeError(f"Unsupported edition condition: {stem}")
                visible = visible and branch == 0
            if visible:
                original.extend(paragraphs[offset:offset + count])
            offset += count
        if ordinal in (0, 15):
            original = original[:2] + [" ".join(original[2:])]
        # Physical source wrapping is not a paragraph break; engine line tags are.
        ruby = "".join(line["raw"].strip() for line in witness["source_lines"])
        ruby = re.sub(r"\[line(\d+)\]", lambda m: "―" * int(m[1]), ruby)
        ruby = ruby.replace("[l][r]", "\n").replace("[lr]", "\n")
        ruby = re.sub(r"\[(?!ruby\s)[^\]]+\]", "", ruby).strip()
        page = next(p for p in pages if p["ref"] == binding["target_ref"])
        if ordinal == 13:
            # The reaction, silence, and appearance have identical Japanese in
            # both witnesses. Keep the published English, not the older draft.
            original[:3] = page["en"].split("\n\n")[:3]
        # The alternate comes wholly from the hash-bound composite. The
        # existing All-ages text is preserved, not replaced by its older draft.
        page["editions"] = {
            "all-ages": {k: page[k] for k in ("ja", "jaRuby", "en")},
            "original": {"ja": re.sub(r"\[ruby\s+text=[^\]]+\]", "", ruby), "jaRuby": ruby, "en": "\n\n".join(original)},
        }
    for ordinal in (1, 9):
        stem = f"hf7-18-page{ordinal}"
        reviewed_path = ROOT / f"campaign/commented_source_restoration_v1/partial_page_variants/{stem}.recovered-second-pass.json"
        binding = json.loads((ROOT / f"engineering/ultimate_english/{stem}-dual-source-candidate/verification.json").read_text())
        if hashlib.sha256(reviewed_path.read_bytes()).hexdigest() != binding["recovered_second_pass_sha256"]:
            raise RuntimeError(f"Edition review changed: {stem}")
        if hashlib.sha256(manuscript.read_bytes()).hexdigest() != binding["canonical_sha256"]:
            raise RuntimeError(f"Edition canonical manuscript changed: {stem}")
        reviewed = json.loads(reviewed_path.read_text())
        source = ROOT / reviewed["source_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != reviewed["source_sha256"]:
            raise RuntimeError(f"Edition Japanese source changed: {stem}")
        source_lines = source.read_text(encoding="utf-8-sig").splitlines()
        for line in reviewed["source_lines"]:
            if source_lines[line["line"] - 1] != line["raw"]:
                raise RuntimeError(f"Edition source binding mismatch: {stem}")
        raw = "\n".join(line["raw"] for line in reviewed["source_lines"])
        ruby = re.sub(r"\[line(\d+)\]", lambda m: "―" * int(m[1]), raw)
        ruby = re.sub(r"\[(?:l|r|lr)\]", "", ruby).replace("　", " ").strip()
        ruby = re.sub(r"\[(?!ruby\s)[^\]]+\]", "", ruby)
        plain = re.sub(r"\[ruby\s+text=[^\]]+\]", "", ruby)
        page = next(p for p in pages if p["ref"] == reviewed["target_ref"])
        if page["en"] != dict(english_pages(manuscript))[reviewed["target_ref"]]:
            raise RuntimeError(f"Published canonical passage differs from edition binding: {stem}")
        page["editions"] = {
            "all-ages": {k: page[k] for k in ("ja", "jaRuby", "en")},
            "original": {"ja": plain, "jaRuby": ruby, "en": reviewed["english"]},
        }


def refresh_editions() -> None:
    """Overlay verified edition text without importing unrelated manuscript edits."""
    index = json.loads((OUT / "index.json").read_text())
    changes = {}
    projected = {}
    projected_concordance = []
    for meta in index["scripts"]:
        path = OUT / f'{meta["id"]}.json'
        before = path.read_text()
        payload = json.loads(before)
        embedded_editions(meta["script"], payload["pages"], EN / f'{meta["script"]}.md')
        after = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if after != before:
            changes[path] = after
        for page in payload["pages"]:
            projected_concordance.append({"scriptId": meta["id"], "script": meta["script"],
                "route": meta["route"], "title": meta["title"],
                **{key: value for key, value in page.items() if key != "mirrorMoon"}})
            if "editions" in page:
                key = (meta["id"], page["ref"])
                if key in projected:
                    raise RuntimeError(f"Ambiguous edition passage: {key}")
                projected[key] = page
    concordance_path = OUT / "concordance.json"
    encoded = json.dumps(projected_concordance, ensure_ascii=False, separators=(",", ":"))
    if encoded != concordance_path.read_text():
        changes[concordance_path] = encoded
    for meta in index["scripts"]:
        payload = json.loads(changes.get(OUT / f'{meta["id"]}.json', (OUT / f'{meta["id"]}.json').read_text()))
        meta["pages"] = len(payload["pages"])
        meta["editionPages"] = {
            edition: sum(edition in page.get("availableEditions", ["original", "all-ages"]) for page in payload["pages"])
            for edition in ("original", "all-ages")
        }
    index["pageCount"] = sum(meta["pages"] for meta in index["scripts"])
    encoded_index = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    if encoded_index != (OUT / "index.json").read_text():
        changes[OUT / "index.json"] = encoded_index
    # All source and projection checks finish before any write.
    for path, content in changes.items():
        path.write_text(content, encoding="utf-8")
    print(json.dumps({"edition_files_updated": len(changes)}))


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
        mm_path = MM / f"{script}.ks"
        mm_pages = comparator_pages(mm_path) if mm_path.exists() else []
        if [x[0] for x in jp_pages] != [x[0] for x in en_pages]:
            raise RuntimeError(f"Page mismatch: {script}")
        mm_by_ref = {}
        for label, text in mm_pages:
            mm_by_ref.setdefault(label, []).append(text)
        mm_seen = {}
        aligned_mm = []
        for label, _ in jp_pages:
            occurrence = mm_seen.get(label, 0)
            witnesses = mm_by_ref.get(label, [])
            aligned_mm.append(witnesses[occurrence] if occurrence < len(witnesses) else "")
            mm_seen[label] = occurrence + 1
        payload = {
            "id": ids[script], "script": script, "route": route, "title": script,
            "pages": [
                {"ref": label, "ja": japanese, "jaRuby": ruby, "en": english,
                 "mirrorMoon": mirror_moon}
                for ((label, japanese), (_, ruby), (_, english), mirror_moon)
                in zip(jp_pages, ruby_pages, en_pages, aligned_mm)
            ],
        }
        if script == "タイガー道場すぺしゃる":
            units_path = SITE / "app/script/bonus" / f"{script}.json"
            checkpoint = json.loads((ROOT / "campaign/supplemental_bonus_v1/second-pass-checkpoint.json").read_text())
            bound = next(x for x in checkpoint["manuscripts"] if x["script"] == script)
            if hashlib.sha256(units_path.read_bytes()).hexdigest() != bound["units_sha256"]:
                raise RuntimeError("Tiger Dojo units differ from the reviewed checkpoint.")
            units = json.loads(units_path.read_text())
            # This scene's two engine pages contain an entire conversation,
            # scrolling credits, then a post-credit exchange. Keep their order.
            payload["pages"] = []
            for unit in units:
                japanese = unit["ja"].replace("[heart]", "♥")
                japanese = re.sub(r"\[(?:lr|r|line\d+)\]", "\n", japanese)
                japanese = re.sub(r"\[[^\]]+\]", "", japanese).strip()
                payload["pages"].append({
                    "ref": f'{unit["page"]}-{unit["ref"]}',
                    "ja": japanese, "jaRuby": japanese, "en": unit["en"],
                    "speaker": unit.get("speaker"), "kind": unit["kind"],
                })
        embedded_editions(script, payload["pages"], en_path)
        payloads.append(payload)
        concordance.extend({"scriptId": ids[script], "script": script, "route": route, "title": script,
                            **{key: value for key, value in page.items() if key != "mirrorMoon"}}
                           for page in payload["pages"])
    scripts = [{**{k:p[k] for k in ("id", "script", "route", "title")}, "pages":len(p["pages"]),
        "editionPages": {edition: sum(edition in page.get("availableEditions", ["original", "all-ages"]) for page in p["pages"])
                         for edition in ("original", "all-ages")}} for p in payloads]
    index = {"scripts": scripts, "scriptCount": len(scripts), "pageCount": sum(x["pages"] for x in scripts)}
    OUT.mkdir(parents=True, exist_ok=True)
    for payload in payloads:
        (OUT / f'{payload["id"]}.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "concordance.json").write_text(json.dumps(concordance, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"scripts": index["scriptCount"], "pages": index["pageCount"], "preserved_ids":len(published)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--editions-only", action="store_true", help="Preserve published prose and update verified edition overlays only")
    if parser.parse_args().editions_only:
        refresh_editions()
    else:
        main()
