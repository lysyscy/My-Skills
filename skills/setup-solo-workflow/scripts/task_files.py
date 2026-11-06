"""Read-only task-file closure, independent of runtime artifact storage."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import subprocess
from urllib.parse import unquote, urlsplit

TEXT = {'.md', '.py', '.ps1', '.sh', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml', '.toml'}
LINK = re.compile(r'\]\((<[^>]+>|[^\s)]+)(?:\s+["\'][^)]*)?\)')


def git(root, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, env=env)
    if result.returncode:
        raise ValueError('Git query failed: ' + ' '.join(args[:2]))
    return result.stdout.decode('utf-8')


def safe(root, path):
    for part in [path, *path.parents]:
        if part.is_symlink() or part.exists() and getattr(part.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('linked/reparse path refused: ' + str(part))
        if part == root:
            return
    raise ValueError('path outside project')


def task_path(value):
    value = value.replace('\\', '/')
    p = PurePosixPath(value)
    if p.is_absolute() or ':' in value or '..' in p.parts or any(x in value for x in '*?[]'):
        raise ValueError('task path must be a literal project-relative path')
    if len(p.parts) < 2 or p.parts[0] != '.scratch':
        raise ValueError('task scope must be below .scratch')
    return p.as_posix()


def within(path, scopes):
    return any(path == scope or path.startswith(scope + '/') for scope in scopes)


def check_task(root, scopes, revision='HEAD', closed=False):
    root = Path(os.path.abspath(root))
    safe(root, root)
    if not root.is_dir() or Path(git(root, 'rev-parse', '--show-toplevel').strip()).resolve() != root.resolve():
        raise ValueError('root must be the Git project root')
    if revision.startswith('-'):
        raise ValueError('invalid revision')
    commit = git(root, 'rev-parse', '--verify', revision + '^{commit}').strip()
    scopes = sorted({task_path(value) for value in scopes})
    if not scopes:
        raise ValueError('at least one explicit task scope is required')
    for scope in scopes:
        safe(root, root / scope)
    historical = {x for x in git(root, 'ls-tree', '-r', '--name-only', '-z', commit, '--', '.scratch').split('\0') if x}
    changed = {x for x in git(root, 'diff', '--name-only', '-z', commit, '--', '.scratch').split('\0') if x}
    selected = {x for x in historical if within(x, scopes)}
    existing = []
    for scope in scopes:
        path = root / scope
        if not path.exists():
            continue
        existing.append(scope)
        pending = [path]
        while pending:
            item = pending.pop()
            safe(root, item)
            if item.is_dir():
                pending.extend(item.iterdir())
            elif item.is_file():
                selected.add(item.relative_to(root).as_posix())
            else:
                raise ValueError('special task file refused')
    files = []
    for name in sorted(selected):
        p = root / name
        safe(root, p)
        exists = p.is_file()
        saved = name in historical
        files.append(dict(path=name, exists=exists, saved_in_revision=saved,
                          unchanged_from_revision=bool(exists and saved and name not in changed)))
    references, unreadable = [], []
    candidates = set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0'))
    for name in sorted(candidates):
        if not name or within(name, scopes) or Path(name).suffix.lower() not in TEXT:
            continue
        p = root / name
        if not p.exists():
            continue
        try:
            safe(root, p)
            text = p.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError, ValueError):
            unreadable.append(name)
            continue
        for number, line in enumerate(text.splitlines(), 1):
            targets = set()
            for match in LINK.finditer(line):
                value = unquote(match.group(1).strip('<>'))
                if urlsplit(value).scheme or value.startswith(('#', '/')):
                    continue
                value = re.sub(r':\d+$', '', value.split('#')[0])
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), value.replace('\\', '/')))
                if within(target, scopes):
                    targets.add(target)
            if p.suffix.lower() != '.md':
                for scope in scopes:
                    if scope in line:
                        targets.add(scope)
            for target in sorted(targets):
                references.append(dict(source=name, line=number, target=target))
    unknown = [s for s in scopes if not any(within(x, [s]) for x in selected) and s not in existing]
    errors = []
    if unknown:
        errors.append('scope absent from both working tree and selected revision')
    if unreadable:
        errors.append('reference scan incomplete')
    if closed and existing:
        errors.append('task material still occupies active paths')
    if closed and references:
        errors.append('live local references still target task scope')
    return dict(ok=not errors, mode='closed' if closed else 'inspect', revision=commit,
                scopes=scopes, existing_paths=existing, files=files, references=references,
                unreadable=unreadable, unknown_scopes=unknown, errors=errors,
                limits='Repository text links and literal code paths only; external consumers and semantic retention require owner review.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--path', action='append', required=True, dest='scopes')
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--closed', action='store_true')
    args = parser.parse_args(argv)
    try:
        report = check_task(args.root, args.scopes, args.revision, args.closed)
    except (OSError, ValueError) as exc:
        report = dict(ok=False, errors=[str(exc)])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
