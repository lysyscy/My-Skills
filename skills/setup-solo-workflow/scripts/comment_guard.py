"""Check changed comments and TypeScript double assertions."""
import argparse
import ast
from bisect import bisect_right
from io import BytesIO
import os
from pathlib import Path
import re
import subprocess
import sys
import tokenize


PYTHON = {'.py', '.pyi'}
TYPESCRIPT = {'.ts', '.tsx', '.cts', '.mts'}
SCRIPT = TYPESCRIPT | {'.js', '.jsx', '.cjs', '.mjs'}
DIRECTIVE = re.compile(
    r'^(?:noqa\b|type:\s*\S|(?:coupling-ignore|SPDX-License-Identifier|fmt|isort|ruff|'
    r'sourceMappingURL|sourceURL)\s*[:=]\s*\S|@ts-(?:check|nocheck|ignore|expect-error)\b|'
    r'(?:eslint|oxlint|biome)-(?:disable|enable|ignore)[\w-]*\b|prettier-ignore\b|'
    r'(?:#|@)__PURE__\b|external-constraint:\s*\S)', re.IGNORECASE,
)
DOC_TAG = re.compile(r'(?m)^\s*@(param|type|returns?|typedef|template|throws|deprecated|public|private|see)\b')
JS_TOKEN = re.compile(r'[$\w]+|=>|\+\+|--|[^\s]')
TEMPLATE_MARKER = re.compile(r'\\[\s\S]|`|\$\{')
JSX_START = re.compile(r'<(?:[A-Za-z_$][\w$.:-]*(?![\w$.:-])(?=[\s/>])(?!\s+(?:extends\b|=))|(?=>))')
JSX_MARKER = {'jsx-text': re.compile(r'</|[<{]'),
              'jsx-tag': re.compile(r'''/>|[>"'{]'''),
              'jsx-close': re.compile(r'>')}
REGEX = re.compile(r'/((?:\\[^\r\n]|\[(?:\\[^\r\n]|[^\]\\\r\n])*\]|[^/\[\\\r\n])+)/[a-z]*')
REGEX_PREFIX = {'', '(', '[', '{', '}', '=', '=>', '!', '~', '?', ':', ';', ',', '&', '|', '+', '-', '*', '%',
                'return', 'throw', 'case', 'delete', 'void', 'typeof', 'yield', 'await', 'in', 'of', 'else', 'do'}
HUNK = re.compile(rb'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
PATTERNS = [f':(glob)**/*{suffix}' for suffix in sorted(PYTHON | SCRIPT)]


def allowed_comment(comment: str, line: int) -> bool:
    if line == 1 and comment.startswith('#!'):
        return True
    if comment.startswith('#') and line <= 2 and re.match(r'#.*?coding[:=]\s*[-\w.]+', comment):
        return True
    if comment.startswith('/*'):
        body = re.sub(r'(?m)^\s*\* ?', '', comment[2:-2].strip())
    else:
        body = comment.removeprefix('//').removeprefix('#').strip()
    return bool(DIRECTIVE.match(body) or (comment.startswith('/**') and DOC_TAG.search(body)))


def quoted_end(source: str, start: int, quote: str) -> int:
    pattern = re.compile(rf'\\[\s\S]|{re.escape(quote)}')
    for match in pattern.finditer(source, start + 1):
        if match[0] == quote:
            return match.end()
    return len(source)


def javascript_tokens(source: str, *, jsx: bool):
    stack = []
    previous = ''
    parens = []
    offset = 0
    while offset < len(source):
        if stack and stack[-1] == 'template':
            match = TEMPLATE_MARKER.search(source, offset)
            if match is None:
                break
            offset = match.end()
            if match[0] == '`':
                stack.pop()
                previous = 'literal'
            elif match[0] == '${':
                stack.append('interpolation')
                previous = '{'
            else:
                continue
            yield (False, match.start(), offset, match[0])
            continue
        if stack and (marker := JSX_MARKER.get(stack[-1])):
            match = marker.search(source, offset)
            if match is None:
                break
            token, offset = match[0], match.end()
            if token in ('"', "'"):
                end = source.find(token, offset)
                offset = len(source) if end < 0 else end + 1
            elif token == '{':
                stack.append('interpolation')
                previous = '{'
            elif token == '<':
                stack.append('jsx-tag')
            elif token == '</':
                stack[-1] = 'jsx-close'
            elif token == '>' and stack[-1] == 'jsx-tag':
                stack[-1] = 'jsx-text'
            else:
                stack.pop()
                previous = 'literal'
            yield (False, match.start(), offset, token)
            continue
        match = JS_TOKEN.search(source, offset)
        if match is None:
            break
        token, start, offset = match[0], match.start(), match.end()
        prefix = source[start:start + 2]
        if prefix == '//' or (start == 0 and prefix == '#!'):
            newline = source.find('\n', start + 2)
            offset = len(source) if newline < 0 else newline
            yield (True, start, offset, source[start:offset])
            continue
        if prefix == '/*':
            close = source.find('*/', start + 2)
            offset = len(source) if close < 0 else close + 2
            yield (True, start, offset, source[start:offset])
            continue
        if token in ('"', "'"):
            offset = quoted_end(source, start, token)
            token = 'literal'
        elif token == '`':
            stack.append('template')
        elif token == '<' and jsx and previous in REGEX_PREFIX and JSX_START.match(source, start):
            stack.append('jsx-tag')
        elif token == '/' and previous in REGEX_PREFIX and (literal := REGEX.match(source, start)):
            offset = literal.end()
            token = 'literal'
        elif stack and token == '{':
            stack.append('brace')
        elif stack and token == '}':
            stack.pop()
        if token == '(':
            parens.append(previous in {'if', 'while', 'for', 'with', 'switch', 'catch'})
        previous = ';' if token == ')' and parens and parens.pop() else token
        yield (False, start, offset, token)


def python_findings(data: bytes, touched) -> list[tuple[int, str]]:
    return [
        (token.start[0], 'COMMENT')
        for token in tokenize.tokenize(BytesIO(data).readline)
        if token.type == tokenize.COMMENT and touched(token.start[0], token.end[0])
        and not allowed_comment(token.string, token.start[0])
    ]


def script_findings(source: str, touched, *, suffix: str, assertions_only: bool) -> list[tuple[int, str]]:
    breaks = [match.end() for match in re.finditer('\n', source)]
    findings = []
    previous = []
    for comment, start, stop, value in javascript_tokens(source, jsx=suffix in {'.jsx', '.tsx'}):
        first = bisect_right(breaks, start) + 1
        last = bisect_right(breaks, stop - 1) + 1
        if comment:
            if not assertions_only and touched(first, last) and not allowed_comment(value, first):
                findings.append((first, 'COMMENT'))
            continue
        if suffix in TYPESCRIPT and [token for token, _ in previous] == ['as', 'unknown'] and value == 'as':
            original = previous[0][1]
            if touched(original, last):
                findings.append((original, 'DOUBLE_ASSERTION'))
        previous = [*previous[-1:], (value, first)]
    return findings


def git(root: Path, *args: str, allowed=(0,)) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ['git', '--no-optional-locks', '-c', 'core.quotePath=true', *args],
        cwd=root, capture_output=True, timeout=30, check=False,
    )
    if result.returncode not in allowed:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip() or f'git {args[0]} failed')
    return result


def patch_lines(patch: bytes) -> dict[str, list[range]]:
    changed = {}
    current = None
    saw_destination = False
    for row in patch.split(b'\n'):
        if row.startswith(b'diff --git '):
            current = None
            saw_destination = False
        elif not saw_destination and row.startswith(b'+++ '):
            saw_destination = True
            path = row[4:].removesuffix(b'\t')
            if path.startswith(b'"'):
                path = ast.literal_eval('b' + path.decode('ascii'))
            if path.startswith(b'b/'):
                current = os.fsdecode(path[2:])
        elif current is not None and (match := HUNK.match(row)):
            start, count = int(match[1]), int(match[2] or 1)
            if count:
                changed.setdefault(current, []).append(range(start, start + count))
    return changed


def listed(root: Path, *args: str) -> list[str]:
    output = git(root, 'ls-files', '-z', *args, '--', *PATTERNS).stdout
    return [os.fsdecode(name) for name in output.split(b'\0') if name]


def selection(root: Path, args) -> dict[str, list[range] | None]:
    if args.files is not None:
        return {Path(name).as_posix(): None for name in args.files}
    if args.tracked:
        return dict.fromkeys(listed(root, '--cached'))
    base = []
    if not args.staged:
        revision = git(root, 'rev-parse', '--verify', '--end-of-options',
                       f'{args.diff}^{{commit}}', allowed=(0, 128))
        if revision.returncode:
            if args.diff != 'HEAD':
                raise ValueError(f'invalid diff base: {args.diff}')
            return dict.fromkeys(listed(root, '--cached', '--others', '--exclude-standard'))
        base = [revision.stdout.decode('ascii').strip()]
    patch = git(
        root, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--no-color', '--word-diff=none',
        '--text', '--unified=0', '--diff-filter=ACMRT', '--src-prefix=a/', '--dst-prefix=b/',
        *(['--cached'] if args.staged else base), '--', *PATTERNS,
    ).stdout
    changed = patch_lines(patch)
    if not args.staged:
        changed.update(dict.fromkeys(listed(root, '--others', '--exclude-standard')))
    return changed


def source_bytes(root: Path, name: str, *, staged: bool, required: bool) -> bytes | None:
    if staged:
        return git(root, 'cat-file', 'blob', f':{name}').stdout
    path = root / name
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'file is outside the checkout: {name}')
    if path.is_symlink() or (not required and not path.exists()):
        return None
    return path.read_bytes()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--staged', action='store_true', help='check added lines in Git index blobs')
    mode.add_argument('--diff', nargs='?', const='HEAD', metavar='BASE', help='check changes and untracked files')
    mode.add_argument('--files', nargs='+', metavar='PATH', help='check all lines in explicit files')
    mode.add_argument('--tracked', action='store_true', help='check all lines in tracked files')
    parser.add_argument('--assertions', action='store_true', help='check TypeScript double assertions only')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.files is None:
            top = git(root, 'rev-parse', '--show-toplevel').stdout.rstrip(b'\r\n')
            if Path(os.fsdecode(top)).resolve() != root:
                raise ValueError('expected a Git checkout root')
        selected = selection(root, args)
        failed = False
        for name, ranges in sorted(selected.items()):
            suffix = Path(name).suffix.lower()
            if suffix not in (TYPESCRIPT if args.assertions else PYTHON | SCRIPT):
                continue
            data = source_bytes(root, name, staged=args.staged, required=args.files is not None)
            if data is None:
                continue

            def touched(first, last, ranges=ranges):
                return ranges is None or any(interval.start <= last and interval.stop > first for interval in ranges)

            findings = (python_findings(data, touched) if suffix in PYTHON else
                        script_findings(data.decode('utf-8-sig'), touched, suffix=suffix,
                                        assertions_only=args.assertions))
            for line, code in findings:
                message = ('keep only directives, API annotations and external constraints' if code == 'COMMENT' else
                           'validate or narrow the value instead of using as unknown as')
                print(f'{name}:{line}: {code} {message}')
                failed = True
        return int(failed)
    except (OSError, RuntimeError, ValueError, SyntaxError, subprocess.SubprocessError, tokenize.TokenError) as error:
        print(f'comment_guard: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
