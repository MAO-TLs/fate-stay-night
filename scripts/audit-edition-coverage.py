"""Inventory source comments without conflating them with confirmed variants."""
import json
import re
import hashlib
from pathlib import Path
from collections import Counter

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent


def normalized(text):
    return re.sub(r"[\s　]", "", re.sub(r"\[[^\]]*\]", "", text)).lstrip(";")


def audit():
    index = json.loads((SITE / "public/data/script/index.json").read_text())
    ids = {s["script"]: s["id"] for s in index["scripts"]}
    records = {}
    target_refs = {}
    exclusions_path = SITE / "app/script/edition-exclusions.json"
    exclusions = {}
    if exclusions_path.exists():
        exclusions = {(item["script"], item["line"]): item
                      for item in json.loads(exclusions_path.read_text())}
    folder = ROOT / "campaign/commented_source_restoration_v1"
    witness_path = folder / "original-witness-audit.json"
    witness = {}
    if witness_path.exists():
        witness = {(f["script"], f["line"]): f for f in json.loads(witness_path.read_text())["findings"]}
    for path in sorted(folder.rglob("*.second-pass.json")):
        record = json.loads(path.read_text())
        for line in record.get("source_lines", []):
            key = (record.get("source_path"), line["line"])
            records.setdefault(key, []).append(str(path.relative_to(ROOT)))
    for record in json.loads((SITE / "app/script/edition-additions.json").read_text()):
        for line in record["source_lines"]:
            key = (f"source/reader/jp/base/{record['script']}.ks", line["line"])
            records.setdefault(key, []).append("site/app/script/edition-additions.json")
            target_refs.setdefault(key, []).append(record["ref"])
    findings = []
    for source in sorted((ROOT / "source/reader/jp/base").glob("*.ks")):
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        payload = json.loads((SITE / "public/data/script" / f"{ids[source.stem]}.json").read_text())
        pages = {p["ref"]: p for p in payload["pages"]}
        ref = None
        for number, raw in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
            match = re.match(r"\*(page\d+)", raw)
            if match:
                ref = match[1]
            if not raw.startswith(";") or raw[1:].startswith(("@", "*")):
                continue
            text = normalized(raw)
            if not re.search(r"[ぁ-んァ-ヶ一-龯]", text):
                continue
            key = (str(source.relative_to(ROOT)), number)
            candidate_refs = [ref, *target_refs.get(key, [])]
            original = "\n".join(pages.get(target, {}).get("editions", {}).get("original", {}).get("ja", "")
                                 for target in candidate_refs)
            exposed = bool(text and text in normalized(original))
            shared = bool(text and text in normalized(pages.get(ref, {}).get("ja", "")))
            exclusion = exclusions.get((source.stem, number))
            findings.append({"script": source.stem, "ref": ref, "line": number,
                "review_records": records.get(key, []), "exposed_in_original": exposed,
                "status": "exposed" if exposed else "identical_source_already_visible" if shared else "reviewed_not_edition_difference" if exclusion else "reviewed_mapping_needed" if key in records else "candidate_not_verified_as_edition"})
            if exclusion:
                findings[-1]["exclusion_reason"] = exclusion["reason"]
            prior = witness.get((source.stem, number))
            if prior:
                findings[-1]["witness_status"] = prior["witness_status"] if prior["local_source_sha256"] == source_hash else "stale_source_binding"
    remaining = Counter(f.get("witness_status", "not_checked") for f in findings
                        if f["status"] not in ("exposed", "identical_source_already_visible", "reviewed_not_edition_difference"))
    return {"note": "Commented text is a candidate, not proof of an edition difference or missing translation. Exposure checks match source text, not translation quality.",
            "counts": dict(Counter(f["status"] for f in findings)),
            "remaining_by_witness": dict(remaining), "findings": findings}


if __name__ == "__main__":
    result = audit()
    print(json.dumps({key: value for key, value in result.items() if key != "findings"}, ensure_ascii=False))
    for item in result["findings"]:
        if item["status"] == "reviewed_mapping_needed":
            print(json.dumps(item, ensure_ascii=False))
