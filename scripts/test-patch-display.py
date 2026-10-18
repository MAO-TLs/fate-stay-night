"""Verify the shipped archive and reject recurring display-command defects."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "patch_tools"))
from xp3 import read
from sweep_script import inspect
from repair_candidate import repair_files

site = HERE.parent
archive = site / "public/downloads/patch_lang_english.xp3"
manifest = json.loads(archive.with_suffix(".manifest.json").read_text())
report = json.loads((site / "public/downloads/patch_display_verification.json").read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest["output_sha256"]
assert archive.stat().st_size == manifest["output_bytes"]
files = read(archive)
assert len(files) == manifest["entries"] == 895
scripts, pages, commands, issues = inspect(files)
assert not issues, issues
assert scripts == report["full_script_scan"]["scripts_checked"] == 734
assert pages == report["full_script_scan"]["page_labels_checked"] == 27918
assert set(commands) <= set(report["full_script_scan"]["command_names"]), sorted(set(commands) - set(report["full_script_scan"]["command_names"]))
assert repair_files(files) == (files, []), "Display cleanup was omitted from the build"
for entry in manifest["display_repair"]["changed_entries"]:
    assert hashlib.sha256(files[entry["entry"]]).hexdigest() == entry["after_sha256"]
assert hashlib.sha256((site / "public/downloads/patch_display_verification.json").read_bytes()).hexdigest() == manifest["display_verification_sha256"]
assert report["archive_sha256"] == manifest["output_sha256"]
assert report["version"] == manifest["version"] == "1.3.0"
assert manifest["runtime_tested"] is False and report["runtime_tested"] is False
parity = report["mirror_moon_display_parity"]
assert parity["candidate_sha256"] == manifest["output_sha256"]
assert parity["remaining_hold_rows"] == 0
assert parity["previous_held_rows_resolved"] == 10
assert parity["profiles_skipped_unaligned"] == 0
assert parity["unknown_condition_comparisons_unresolved"] == 0
assert parity["unknown_condition_edition_comparisons_enumerated"] == 110
assert parity["edition_rows_checked"] == 48408
assert parity["matching_edition_rows"] + parity["raw_mirror_mismatch_rows"] == parity["edition_rows_checked"]
assert parity["raw_mirror_mismatch_rows"] == len(parity["source_supported_divergences"])
assert parity["residuals_exactly_match_reviewed_source_divergences"]
print(f"PASS: archive hash, {scripts} scripts / {pages} labels, display-command guards, repair idempotence, and final static parity evidence")
