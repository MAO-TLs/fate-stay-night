"""Check every XP3 script for the reproduced display-command defects.

This is a syntax/structure gate, not a proof of all native game routes. Quoted
attributes may contain inline tags, so scanning a tag cannot stop at the first
closing bracket. Compare new command names against the supplied engine witness.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import sys

from xp3 import read


def active_lines(text):
    script = comment = False
    for number, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("/*"):
            comment = True
        if comment:
            if "*/" in s:
                comment = False
            continue
        if s.startswith("@iscript"):
            script = True
        if script:
            if s.startswith("@endscript"):
                script = False
            continue
        if s and not s.startswith(";") and not line.startswith("*"):
            yield number, line


def inline_tags(line):
    i = 0
    while i < len(line):
        if line[i] != "[":
            i += 1
            continue
        if line[i:i+2] == "[[":
            i += 2
            continue
        start = i
        i += 1
        quote = False
        while i < len(line):
            if line[i] == '"':
                quote = not quote
            if line[i] == "]" and not quote:
                break
            i += 1
        if i == len(line):
            raise ValueError(f"Unclosed inline tag: {line[start:]}")
        body = line[start+1:i]
        yield body
        # Text attributes are recursively interpreted by align/doublecolumn.
        for value in re.findall(r'\b(?:text|upper|lower)="([^"]*)"', body):
            yield from inline_tags(value)
        i += 1


def inspect(files):
    commands = collections.Counter()
    issues = []
    scripts = pages = 0
    for name, data in files.items():
        if not name.endswith(".ks"):
            continue
        scripts += 1
        text = data.decode("utf-16")
        pages += len(re.findall(r"^\*page\d+(?:\||\s*$)", text, re.M))
        for number, line in active_lines(text):
            s = line.strip()
            bodies = [s[1:]] if s.startswith("@") else list(inline_tags(line))
            for body in bodies:
                tag = body.split()[0].lower() if body.split() else ""
                commands[tag] += 1
                if tag in {"align", "doublecolumn"}:
                    # An embedded ASCII quote can end a text attribute early;
                    # merely checking an even quote count would miss that.
                    rest = body[len(body.split()[0]):]
                    attr = re.compile(r'''\s+[A-Za-z]\w*=(?:"[^"]*"|'[^']*'|[^\s"']+)''')
                    while rest.strip():
                        match = attr.match(rest)
                        if not match:
                            issues.append({"entry": name, "line": number, "kind": "malformed_display_attributes"})
                            break
                        rest = rest[match.end():]
                if tag == "align":
                    val = re.search(r'\btext="([^"]*)"', body)
                    if val and re.search(r"\[(?:lr|r)\]", val[1]):
                        issues.append({"entry": name, "line": number, "kind": "multiline_alignment"})
                if "Presentation-only continuation." in body:
                    issues.append({"entry": name, "line": number, "kind": "editorial_sentinel"})
                if s.startswith("@"):
                    for value in re.findall(r'\b(?:text|upper|lower)="([^"]*)"', body):
                        for inner in inline_tags(value):
                            commands[inner.split()[0].lower()] += 1
    return scripts, pages, commands, issues


def sweep(baseline, candidate):
    before, after = read(baseline), read(candidate)
    _, _, old_commands, _ = inspect(before)
    scripts, pages, commands, issues = inspect(after)
    new_commands = sorted(set(commands) - set(old_commands))
    # font/resetfont are native KAG commands used by authored emphasis.
    unexpected = [t for t in new_commands if t not in {"font", "resetfont"}]
    return {"archive_sha256": hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),
            "scripts_checked": scripts, "page_labels_checked": pages,
            "command_names": sorted(commands), "new_command_names": new_commands,
            "unexpected_new_commands": unexpected, "issues": issues,
            "passed": not issues and not unexpected,
            "scope": "All script entries, active command syntax; not a full native playthrough."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = sweep(args.baseline, args.candidate)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"command_names"}}, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
