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
native = report["native_display_sweep"]
assert native["completed"] and native["cases"] == native["expected_cases"]
assert native["nonblank_clipping_cases"] == 0
assert set(native["registered_bundled_typefaces"]) == {"Calibri", "Bernhard Modern Std", "Sabon Next LT Pro"}
assert native["case_count_by_script_edition"] == {"original": 666, "all-ages": 666}
additional = report["additional_targeted_native_comparison"]
assert additional["completed"] and additional["cases"] == 18
assert all(not (r["nonblank_canvas_clips"] or r["nonblank_line_buffer_clips"]) for r in additional["records"] if ':FIX:' in r["case"] or ':MM:' in r["case"])
print(f"PASS: archive hash, {scripts} scripts / {pages} labels, display-command guards, repair idempotence, and native evidence binding")
