"""Project native KAG text into occurrence-aware browser pages.

This is a static transcript, not a KAG interpreter. Edition settings are explicit;
other text-dependent conditions and graphical spell effects must be supplied by
the caller. Unknown text controls fail closed. No source wording is reauthored.
Physical source newlines are soft spaces, while native line/paragraph and screen
breaks become paragraph separators. Native labels do not reset conditional state.
"""
from __future__ import annotations

import re
from typing import Mapping


class ProjectionError(ValueError):
    pass


_UNKNOWN = object()
_EFFECTS = {'block', 'wacky', 'aero', 'margos', 'keraino'}
# These tags affect sound, graphics, timing, or text positioning, not characters.
_INLINE_PRESENTATION = {
    'l', 'nolr', 'indent', 'endindent', 'wait', 'chgfg', 'wsay',
    'shock', 'se', 'quake', 'clfg', 'playstop', 'dash', 'wdash', 'say', 'ld',
    'locate', 'link', 'endlink', 'resetstyle', 'style',
}
_GLYPHS = {'heart': '♥', 'auml': 'ä', 'ouml': 'ö', 'uuml': 'ü', 'szlig': 'ß'}


def _compact(value: str) -> str:
    """Remove expression whitespace except inside quoted strings."""
    result = []; quote = None; escaped = False
    for char in value:
        if escaped:
            result.append(char); escaped = False
        elif quote and char == '\\':
            result.append(char); escaped = True
        elif quote:
            result.append(char)
            if char == quote: quote = None
        elif char in "\"'":
            quote = char; result.append(char)
        elif not char.isspace(): result.append(char)
    return ''.join(result)


def _split(value: str, operator: str) -> list[str]:
    result = []; quote = None; escaped = False; depth = 0; start = 0; i = 0
    while i < len(value):
        char = value[i]
        if escaped: escaped = False
        elif quote and char == '\\': escaped = True
        elif quote:
            if char == quote: quote = None
        elif char in "\"'": quote = char
        elif char in '([': depth += 1
        elif char in ')]': depth -= 1
        elif not depth and value.startswith(operator, i):
            result.append(value[start:i]); i += len(operator); start = i; continue
        i += 1
    return result + [value[start:]] if result else [value]


def _outer(value: str) -> str:
    while value.startswith('(') and value.endswith(')'):
        depth = 0; quote = None; wraps = True
        for i, char in enumerate(value):
            if quote:
                if char == quote: quote = None
            elif char in "\"'": quote = char
            elif char == '(': depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0 and i != len(value) - 1: wraps = False; break
        if not wraps: break
        value = value[1:-1]
    return value


def _and(values):
    values = list(values)
    if any(value is not _UNKNOWN and not bool(value) for value in values): return False
    return _UNKNOWN if any(value is _UNKNOWN for value in values) else True


def _or(values):
    values = list(values)
    if any(value is not _UNKNOWN and bool(value) for value in values): return True
    return _UNKNOWN if any(value is _UNKNOWN for value in values) else False


def _not(value):
    return _UNKNOWN if value is _UNKNOWN else not bool(value)


def _evaluate(expression: str, values: Mapping[str, object]):
    value = _outer(_compact(expression))
    if value in values: return values[value]
    for op, join in [('||', _or), ('&&', _and)]:
        parts = _split(value, op)
        if len(parts) > 1: return join(_evaluate(part, values) for part in parts)
    for op in ('===', '!==', '==', '!=', '<=', '>=', '<', '>'):
        parts = _split(value, op)
        if len(parts) == 2:
            left, right = (_evaluate(part, values) for part in parts)
            if left is _UNKNOWN or right is _UNKNOWN: return _UNKNOWN
            if op in ('==', '==='): return type(left) is type(right) and left == right
            if op in ('!=', '!=='): return type(left) is not type(right) or left != right
            if op == '<': return left < right
            if op == '>': return left > right
            if op == '<=': return left <= right
            return left >= right
    if value.startswith('!'): return _not(_evaluate(value[1:], values))
    if value == 'true': return True
    if value == 'false': return False
    if re.fullmatch(r'-?\d+', value): return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'": return value[1:-1]
    return _UNKNOWN


def attributes(body: str) -> tuple[str, dict[str, str]]:
    """Parse quoted attributes, including inline tags within display strings."""
    match = re.match(r'\s*([^\s]+)', body)
    if not match: raise ProjectionError('Empty command')
    name = match[1].lower(); rest = body[match.end():]; result = {}
    pattern = re.compile(r'''\s+([\w-]+)=(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|([^\s"']+))''')
    while rest.strip():
        match = pattern.match(rest)
        if not match: raise ProjectionError(f'Malformed attributes: {body!r}')
        result[match[1]] = next(part for part in match.groups()[1:] if part is not None)
        rest = rest[match.end():]
    return name, result


def _tokens(text: str):
    """Yield (is_tag, value); closing brackets within strings are not delimiters."""
    cursor = 0; plain = []
    while cursor < len(text):
        if text[cursor:cursor + 2] == '[[':
            plain.append('['); cursor += 2; continue
        if text[cursor] != '[':
            plain.append(text[cursor]); cursor += 1; continue
        if plain: yield False, ''.join(plain); plain = []
        start = cursor + 1; cursor += 1; quote = None; escaped = False
        while cursor < len(text):
            char = text[cursor]
            if escaped: escaped = False
            elif quote and char == '\\': escaped = True
            elif quote:
                if char == quote: quote = None
            elif char in "\"'": quote = char
            elif char == ']': break
            cursor += 1
        if cursor == len(text): raise ProjectionError(f'Unclosed inline tag: {text[start - 1:]!r}')
        yield True, text[start:cursor]; cursor += 1
    if plain: yield False, ''.join(plain)


class _Text:
    def __init__(self, values, effects):
        self.values = values; self.effect_renderings = effects; self.parts = []; self.units = []
        self.effects = []; self.italic = False

    def text(self, value):
        self.parts.append(value)

    def break_(self):
        # Balance emphasis independently in each browser paragraph.
        if self.italic:
            self.parts = [''.join(self.parts).rstrip(), '*']
        self.parts.append('\n\n')
        if self.italic: self.parts.append('*')

    def font(self, italic):
        if self.italic != italic: self.parts.append('*'); self.italic = italic

    def render(self, value):
        for is_tag, part in _tokens(value):
            if not is_tag: self.text(part); continue
            self.command(part, inline=True)

    def command(self, body, inline=False):
        # Font-family values may be KAG expressions containing spaces and
        # embedded quotes. Only the static italic flag changes browser prose.
        if re.match(r'^font(?:\s|$)', body, re.I) and 'italic=' not in body and 'cond=' not in body:
            return
        name, attrs = attributes(body)
        if 'cond' in attrs:
            enabled = _evaluate(attrs['cond'], self.values)
            if enabled is _UNKNOWN: raise ProjectionError(f'Unknown command condition: {attrs["cond"]}')
            if not enabled: return
        if name in ('align', 'doublecolumn', 'staffrolltext'):
            keys = ('upper', 'lower') if name == 'doublecolumn' else ('text',)
            for index, key in enumerate(keys):
                if key not in attrs: raise ProjectionError(f'Missing {key} in {name}')
                if attrs[key].startswith('&'): raise ProjectionError(f'Dynamic {name} text: {attrs[key]}')
                if index: self.break_()
                self.render(attrs[key].strip())
            return
        if name in ('lr', 'r', 'br'): self.break_(); return
        if name in ('pg', 'pgnl', 'pgtg', 'cm', 'ct'):
            self.units.append(self.finish()); self.parts = ['*'] if self.italic else []; return
        if name == 'font':
            if 'italic' in attrs:
                if attrs['italic'] not in ('true', 'false', '1', '0'): raise ProjectionError('Dynamic italic attribute')
                self.font(attrs['italic'] in ('true', '1'))
            return
        if name in ('resetfont', 'rf'): self.font(False); return
        if name == 'ruby': return  # Base characters follow the reading directive.
        if name == 'ch':
            if 'text' not in attrs: raise ProjectionError('ch without static text')
            self.render(attrs['text']); return
        if name in _GLYPHS: self.text(_GLYPHS[name]); return
        if re.fullmatch(r'line\d+', name): self.text('—' * int(name[4:])); return
        if name in _EFFECTS:
            self.effects.append(body)
            key = body if body in self.effect_renderings else name
            if key not in self.effect_renderings:
                raise ProjectionError(f'Graphical text effect needs an explicit reader rendering: {body}')
            self.text(self.effect_renderings[key]); return
        if inline and name not in _INLINE_PRESENTATION:
            raise ProjectionError(f'Unknown inline text command: {name}')

    def finish(self):
        value = ''.join(self.parts).rstrip() + ('*' if self.italic else '')
        # Source-file newlines become soft spaces before reaching this method;
        # only deliberate native breaks are present here.
        paragraphs = []
        for paragraph in re.split(r'\n+', value):
            paragraph = re.sub(r'[^\S\n]+', ' ', paragraph).strip()
            paragraph = re.sub(r'\s+([,.!?;:、。」])', r'\1', paragraph)
            if paragraph and paragraph != '**': paragraphs.append(paragraph)
        return '\n\n'.join(paragraphs)


def project_script(text: str, edition: str, *, conditions: Mapping[str, object] | None = None,
                   effects: Mapping[str, str] | None = None) -> list[dict]:
    """Return native page occurrences with `ordinal`, `ref`, `en`, `display_units`.

    `conditions` maps exact runtime variables or complete atoms to explicit values.
    Only edition variables are supplied automatically. `effects` binds graphical
    text macros to reviewed browser renderings. Unknown text-dependent gates and
    effect renderings raise ProjectionError with the source line number. Screen
    clears inside a native page are retained in display_units. This function does
    not follow jumps or execute TJS, and must not be used to infer route traversal.
    """
    if edition not in ('original', 'all-ages'): raise ValueError(f'Unknown edition: {edition}')
    values = {'sf.gtext': 'classic' if edition == 'original' else 'realta',
              'sf.gmature': edition == 'original', 'sf.ghentai': edition == 'original'}
    values.update({_compact(k): v for k, v in (conditions or {}).items()})
    result = []; stack = []; comment = script = False; current = None; out = None

    def close():
        if current is None: return
        tail = out.finish()
        units = out.units + ([tail] if tail else [])
        current.update(en='\n\n'.join(part for part in units if part), display_units=units, effects=out.effects)
        result.append(current)

    for number, raw in enumerate(text.splitlines(), 1):
        value = raw.strip()
        if value.startswith('/*'): comment = True
        if comment:
            if '*/' in value: comment = False
            continue
        if value.startswith(';'): continue
        if re.match(r'@iscript\b', value): script = True
        if script:
            if re.match(r'@endscript\b', value): script = False
            continue
        label = re.match(r'^\*(page\d+)(?:\||\s*$)', raw)
        if label:
            italic = out.italic if out is not None else False
            close(); current = {'ordinal': len(result), 'ref': label[1], 'line': number}
            out = _Text(values, effects or {})
            if italic: out.font(True)
            continue
        conditional = re.match(r'@(if|ignore|elsif|else|endif|endignore)\b(.*)', value)
        try:
            if conditional:
                op, body = conditional.groups()
                if op in ('if', 'ignore', 'elsif'):
                    _, attrs = attributes(op + body)
                    if 'exp' not in attrs: raise ProjectionError(f'{op} without expression')
                    enabled = _evaluate(attrs['exp'], values)
                if op in ('if', 'ignore'):
                    if op == 'ignore': enabled = _not(enabled)
                    stack.append({'active': enabled, 'taken': enabled, 'expression': attrs['exp'], 'op': op})
                elif op in ('else', 'elsif'):
                    if not stack: raise ProjectionError(f'Orphan {op}')
                    frame = stack[-1]
                    enabled = True if op == 'else' else enabled
                    frame['active'] = _and((_not(frame['taken']), enabled))
                    frame['taken'] = _or((frame['taken'], frame['active']))
                else:
                    if not stack: raise ProjectionError(f'Orphan {op}')
                    frame = stack.pop()
                    if (frame['op'] == 'ignore') != (op == 'endignore'): raise ProjectionError('Mismatched conditional terminator')
                continue
            if current is None or not value or raw.startswith('*'): continue
            enabled = _and(frame['active'] for frame in stack)
            if enabled is False: continue
            if enabled is _UNKNOWN:
                # Ignore purely visual/audio commands; fail on prose, text-bearing
                # commands, font changes, breaks, and clears under uncertain gates.
                if not value.startswith('@') or re.match(r'@(?:align|doublecolumn|staffrolltext|ch|font|rf|resetfont|r|pg|pgnl|pgtg|cm|ct)\b', value):
                    raise ProjectionError('Unknown text condition: ' + ' / '.join(frame['expression'] for frame in stack if frame['active'] is _UNKNOWN))
                continue
            if value.startswith('@'):
                # Parse only text-affecting commands; engine graphics commands
                # may contain syntax which is deliberately outside this parser.
                if re.match(r'@(?:align|doublecolumn|staffrolltext|ch|font|rf|resetfont|r|pg|pgnl|pgtg|cm|ct|ruby)\b', value): out.command(value[1:])
            else:
                out.render(value)
                out.text(' ')
        except ProjectionError as exc:
            raise ProjectionError(f'line {number}: {exc}') from exc
    if stack: raise ProjectionError('Unclosed conditional')
    if comment or script: raise ProjectionError('Unclosed comment or script block')
    close()
    return result
