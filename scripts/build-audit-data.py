#!/usr/bin/env python3
"""Build script-scoped public annotations from the adjudicated mirror moon ledger."""

from collections import defaultdict
from pathlib import Path
import json
import shutil

SITE = Path(__file__).resolve().parents[1]
AUDIT = SITE.parent / "audit" / "mirror_moon_v1"
OUT = SITE / "public" / "data" / "audit" / "findings"


def read(path: Path):
    return json.loads(path.read_text())


def main():
    dossiers = read(AUDIT / "dossiers.json")
    index = read(SITE / "public" / "data" / "script" / "index.json")
    scripts = {item["script"]: item for item in index["scripts"]}
    memberships = defaultdict(list)
    dossier_labels = {}
    for group in dossiers["groups"]:
        for dossier in group["dossiers"]:
            dossier_labels[dossier["id"]] = dossier["title"]
            for finding_id in dossier["findingIds"]:
                memberships[finding_id].append(dossier["id"])

    documents = [read(AUDIT / "ledger.json")]
    documents += [read(path) for path in sorted((AUDIT / "ledger_tranches").glob("*.json"))]
    by_script = defaultdict(list)
    finding_ids = set()
    unmapped = []
    for document in documents:
        script = document["script"]
        script_meta = scripts.get(script)
        if not script_meta:
            raise ValueError(f"Audit script is absent from public index: {script}")
        public_pages = {
            page["ref"]
            for page in read(SITE / "public" / "data" / "script" / f'{script_meta["id"]}.json')["pages"]
        }
        for finding in document["findings"]:
            if finding["id"] in finding_ids:
                raise ValueError(f'Duplicate finding id: {finding["id"]}')
            finding_ids.add(finding["id"])
            record = {
                "id": finding["id"],
                "ref": finding["page"],
                "category": finding["class"],
                "status": finding.get("status", "confirmed_primary"),
                "highlight": finding["eng"],
                "evidenceJa": finding["jp"],
                "governingReading": finding.get("governing_reading", ""),
                "explanation": finding["effect"],
                "dossiers": memberships.get(finding["id"], []),
            }
            if finding["page"] not in public_pages:
                unmapped.append({"script": script, **record})
                continue
            by_script[script_meta["id"]].append(record)

    if len(finding_ids) != dossiers["corpusConfirmedFindingCount"]:
        raise ValueError(
            f'Ledger has {len(finding_ids)} findings; dossiers report '
            f'{dossiers["corpusConfirmedFindingCount"]}'
        )
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    routes = []
    for script_id, findings in sorted(by_script.items()):
        payload = {
            "schema": "fsn-mirror-moon-editorial-errors/1",
            "scriptId": script_id,
            "findingCount": len(findings),
            "findings": findings,
        }
        (OUT / f"{script_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        routes.append({"scriptId": script_id, "findingCount": len(findings)})
    public_index = {
        "schema": "fsn-mirror-moon-editorial-error-index/1",
        "totalFindings": len(finding_ids),
        "mappedFindings": sum(item["findingCount"] for item in routes),
        "unmappedFindings": len(unmapped),
        "withheldBorderlineCount": dossiers["withheldBorderlineCount"],
        "dossierLabels": dossier_labels,
        "routes": routes,
        "unmapped": unmapped,
    }
    (OUT / "index.json").write_text(
        json.dumps(public_index, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    print(json.dumps({
        "total": len(finding_ids),
        "mapped": public_index["mappedFindings"],
        "unmapped": len(unmapped),
        "scripts": len(routes),
    }))


if __name__ == "__main__":
    main()
