"""Classify comment candidates against a pinned Japanese witness, not English.

Matches establish presence in this third-party witness, not original-disc
authenticity. Nonmatches remain unresolved; filename/page alignment can differ.
The generated report never rewrites or publishes reader text.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
from collections import Counter
from urllib.parse import quote

SPEC = importlib.util.spec_from_file_location("coverage", Path(__file__).with_name("audit-edition-coverage.py"))
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)
COMMIT = "60004b118bac19b4c5c2837be8043f393619ec16"
BASE = f"https://raw.githubusercontent.com/fatedev/FATE/{COMMIT}/scenario/"


def prose_pages(text):
    pages, ref = {}, None
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        match = re.match(r"\*(page\d+)(?:\||$)", line)
        if match:
            ref = match[1]
            pages.setdefault(ref, [])
        elif ref and line and not line.startswith(("@", ";", "*")):
            pages[ref].append(line)
    return {ref: coverage.normalized("".join(lines)) for ref, lines in pages.items()}


def fetch(script):
    url = BASE + quote(script + ".ks")
    try:
        data = subprocess.run(["curl", "-fsSL", "--max-time", "30", url],
                              check=True, capture_output=True).stdout
        return script, {"url": url, "sha256": hashlib.sha256(data).hexdigest(),
                        "pages": prose_pages(data.decode("utf-8-sig"))}
    except Exception as error:
        return script, {"url": url, "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates = [f for f in coverage.audit()["findings"]
                  if f["status"] == "candidate_not_verified_as_edition"]
    scripts = sorted({f["script"] for f in candidates})
    with ThreadPoolExecutor(max_workers=6) as pool:
        witnesses = dict(pool.map(fetch, scripts))
    for finding in candidates:
        source = coverage.ROOT / "source/reader/jp/base" / (finding["script"] + ".ks")
        data = source.read_bytes()
        text = coverage.normalized(data.decode("utf-8-sig").splitlines()[finding["line"] - 1])
        witness = witnesses[finding["script"]]
        matches = [ref for ref, prose in witness.get("pages", {}).items() if text in prose]
        finding.update({"local_source_sha256": hashlib.sha256(data).hexdigest(),
                        "witness_url": witness["url"], "witness_sha256": witness.get("sha256"),
                        "matching_witness_pages": matches,
                        "witness_status": "fetch_failed" if "error" in witness else
                        "present_same_page" if finding["ref"] in matches else
                        "present_other_page" if matches else "not_found_unresolved"})
        if "error" in witness:
            finding["error"] = witness["error"]
    report = {"commit": COMMIT,
              "limits": "Third-party Japanese witness, not an authenticated disc rip. Presence does not certify translation; nonmatches are not automatically discarded.",
              "counts": dict(Counter(f["witness_status"] for f in candidates)),
              "scripts_checked": len(scripts), "findings": candidates}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "findings"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
