"""Prepare a local, unpublished repair of reproduced v1.2.0 display defects.

Input is pinned to the independently downloaded public archive. Center each
explicit line separately, split the overwide Sakura sentence at its sentence
boundary, and remove one editorial sentinel and its added line wait. No dialogue
wording changes. This does not modify the input archive or publish anything.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

from xp3 import read, write

RELEASE_SHA = "52a167e9d95fb7409e5f418332bc76d9058caa1bca8fe2c86426cedb60d27d55"
ALIGN = re.compile(r'(?m)^(@align anchor="center" text=")([^"\r\n]*\[lr\][^"\r\n]*)("\r?$)')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def display_normalized(text):
    """Flatten only the permitted display edits to verify all other content."""
    text = text.replace('[Presentation-only continuation.]', '')
    text = re.sub(r'(?m)^@align anchor="center" text="([^"\r\n]*)"\r?$', r'\1', text)
    text = re.sub(r'\[align anchor="center" text="([^"\r\n]*)"\]', r'\1', text)
    text = text.replace('[lr]', ' ')
    text = re.sub(r'(?m)^@lr\r?$', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def repair_files(baseline, strict=False):
    """Idempotent display cleanup, also used by the manuscript release builder."""
    files = dict(baseline)
    edits = []
    for name, data in baseline.items():
        if not name.endswith(".ks"):
            continue
        text = data.decode("utf-16")
        original = text
        def split_centered(match):
            parts = match[2].split("[lr]")
            edits.append({"entry": name, "kind": "center_each_explicit_line", "lines": len(parts)})
            # Literal [lr] becomes the same standalone lr handler; every line
            # receives a fresh centering calculation using its own width.
            return '\r\n@lr\r\n'.join(match[1] + part + '"' for part in parts) + '\r'
        text = ALIGN.sub(split_centered, text)
        if name == "桜ルート十六日目-20.ks":
            old = '@align anchor="center" text="“Let\'s go home, Sakura. It\'s time to sever your ties with that thing.”"'
            new = '@align anchor="center" text="“Let\'s go home, Sakura."\r\n@lr\r\n@align anchor="center" text="It\'s time to sever your ties with that thing.”"'
            # Verify wording independently of the new display-line boundary.
            assert re.sub(r'\s+', ' ', " ".join(re.findall(r'text="([^"]*)"', new))) == re.search(r'text="([^"]*)"', old)[1]
            if old in text:
                assert text.count(old) == 1
                text = text.replace(old, new)
                edits.append({"entry": name, "kind": "split_overwide_centered_sentence", "ref": "page40"})
        if name == "桜ルート八日目-24.ks":
            sentinel = '[lr]\r\n  [Presentation-only continuation.]\r\n'
            if sentinel in text:
                assert text.count(sentinel) == 1
                text = text.replace(sentinel, '\r\n')
                edits.append({"entry": name, "kind": "remove_editorial_sentinel_and_its_line_wait", "ref": "page0"})
        if name == "セイバールート十五日目-19.ks":
            old = '[align anchor="center" text="I learned it from the deaths of all the people I had failed to save."]'
            new = '[align anchor="center" text="I learned it from the deaths"][lr]\r\n[align anchor="center" text="of all the people I had failed to save."]'
            assert re.sub(r'\s+', ' ', " ".join(re.findall(r'text="([^"]*)"', new))) == re.search(r'text="([^"]*)"', old)[1]
            if old in text:
                assert text.count(old) == 1
                text = text.replace(old, new)
                edits.append({"entry": name, "kind": "split_overwide_centered_sentence", "ref": "page67"})
        if name == "ラストエピソード.ks":
            old = '@align anchor="center" text="“[line3]I don’t need it. I can’t wish for something like that.”"'
            new = '@align anchor="center" text="“[line3]I don’t need it."\r\n@lr\r\n@align anchor="center" text="I can’t wish for something like that.”"'
            assert re.sub(r'\s+', ' ', " ".join(re.findall(r'text="([^"]*)"', new))) == re.search(r'text="([^"]*)"', old)[1]
            if old in text:
                assert text.count(old) == 1
                text = text.replace(old, new)
                edits.append({"entry": name, "kind": "split_overwide_centered_sentence", "ref": "page39"})
        if text != original:
            files[name] = text.encode("utf-16")
    if strict:
        assert sum(e["kind"] == "center_each_explicit_line" for e in edits) == 5
        assert len(edits) == 9
    assert not any("[Presentation-only continuation.]" in b.decode("utf-16") for n, b in files.items() if n.endswith(".ks"))
    assert not any(ALIGN.search(b.decode("utf-16")) for n, b in files.items() if n.endswith(".ks"))
    return files, edits


def repair(input_path, output_path):
    assert digest(input_path.read_bytes()) == RELEASE_SHA, "Input differs from examined public v1.2.0"
    baseline = read(input_path)
    files, edits = repair_files(baseline, strict=True)
    assert repair_files(files) == (files, []), "Display cleanup must be idempotent"
    for name, data in baseline.items():
        if not name.endswith(".ks"):
            assert files[name] == data
        else:
            old, new = data.decode("utf-16"), files[name].decode("utf-16")
            assert display_normalized(old) == display_normalized(new), (name, "non-display content changed")
            for pattern in (r"^\*page\d+.*$", r"^\s*@(pg|pgnl|pgtg)\b"):
                assert re.findall(pattern, old, re.M) == re.findall(pattern, new, re.M)
            assert re.findall(r"\[line\d+\]", old) == re.findall(r"\[line\d+\]", new)
    write(output_path, files)
    assert read(output_path) == files
    changed = [{"entry": n, "before_sha256": digest(baseline[n]), "after_sha256": digest(b)} for n, b in files.items() if b != baseline[n]]
    return {"status": "verified_display_candidate", "input_sha256": RELEASE_SHA,
            "candidate_sha256": digest(output_path.read_bytes()), "archive_entries": len(files),
            "changed_entries": changed, "edits": edits,
            "limits": "Runtime evidence is tracked separately. Not a full-route playthrough."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = repair(args.input, args.output)
    args.output.with_suffix(".repair.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
