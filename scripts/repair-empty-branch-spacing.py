"""Repair space-only KAG edition branches without changing words or commands.

Builds a separate candidate from the released v1.3.1 archive. This is a package
regression check, not proof of native font rendering or a full playthrough.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from patch_tools.xp3 import read, write

BASE_SHA256 = '2827e92bd83d5aaea40967af87f6a5d30cba1419c4c85664687858d21056eb89'
EMPTY_BRANCH = re.compile(
    r'(?m)^@if exp="sf\.gtext[^\r\n]+\r?\n[ \t]*\r?\n'
    r'@else\r?\n[ \t]*\r?\n@endif\r?\n')


def repair(text):
    changes = []
    # Reverse edits keep all reported source offsets stable.
    for match in reversed(list(EMPTY_BRANCH.finditer(text))):
        start, end = match.span()
        before = text[start:end]
        after = re.sub(r'(?m)^[ \t]+(?=\r?$)', '', before)
        previous = text[:start].splitlines()[-1] if start else ''
        following = re.match(r'([ \t]+)([^\r\n]+)', text[end:])
        # No explicit break/effect on the preceding prose: the next physical
        # line continues the same sentence. Preserve exactly one word space.
        joins = bool(previous.startswith('  ') and previous.strip()
                     and not re.search(r'[\[\]]', previous)
                     and following and following[2].strip()
                     and not following[2].startswith(('@', '*', ';', '[')))
        if joins:
            suffix = '' if previous.endswith((' ', '\t')) else ' '
            after += suffix
            end += len(following[1])
        if text[start:end] != after:
            changes.append({'offset': start, 'joinedContinuation': joins,
                            'before': text[start:end], 'after': after})
            text = text[:start] + after + text[end:]
    return text, list(reversed(changes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assert args.baseline.resolve() != args.output.resolve()
    assert hashlib.sha256(args.baseline.read_bytes()).hexdigest() == BASE_SHA256
    files = read(args.baseline)
    original = dict(files)
    edits = []
    for entry, payload in files.items():
        if not entry.endswith('.ks'):
            continue
        before = payload.decode('utf-16')
        after, changes = repair(before)
        if changes:
            # All non-whitespace bytes, command lines and labels are unchanged.
            assert re.sub(r'\s', '', before) == re.sub(r'\s', '', after)
            assert [x for x in before.splitlines() if x.startswith(('@', '*'))] == [x for x in after.splitlines() if x.startswith(('@', '*'))]
            assert repair(after)[0] == after
            files[entry] = after.encode('utf-16')
            edits.append({'entry': entry, 'changes': changes})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, files)
    assert read(args.output) == files
    assert original.keys() == files.keys()
    assert all(original[n] == files[n] for n in files if not n.endswith('.ks'))
    report = {'base_sha256': BASE_SHA256,
              'candidate_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
              'changedScripts': len(edits), 'emptyBranches': sum(len(e['changes']) for e in edits),
              'joinedContinuations': sum(c['joinedContinuation'] for e in edits for c in e['changes']),
              'nativeRuntimeTested': False, 'edits': edits}
    args.output.with_suffix('.spacing-proof.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'edits'}, indent=2))


if __name__ == '__main__':
    main()
