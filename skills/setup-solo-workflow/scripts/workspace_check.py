"""Resolve fixed workspace paths and check a task's output/closure without writes."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import stat
import sys

KINDS = ('logs', 'reports', 'screenshots', 'traces', 'exports', 'downloads', 'work', 'recovery')
TASK_FILES = {'spec.md', 'research.md', 'questions.md', 'map.md', 'evidence.md', 'handoff.md'}


def slug(value: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise ValueError('effort/run must be an ASCII slug, at most 80 characters')
    return value


def paths(root: Path, effort: str, run: str) -> dict[str, str]:
    effort, run = slug(effort), slug(run)
    relative = {
        'task': f'.scratch/{effort}', 'history': f'docs/archive/{effort}',
        'archive': f'.artifacts/archive/{effort}',
        **{kind: f'.artifacts/active/{effort}/{run}/{kind}' for kind in KINDS},
        'source_data': 'data/source', 'reference_data': 'data/reference',
        'deliverables': 'exports', 'source': 'src', 'tests': 'tests',
        'fixtures': 'tests/fixtures', 'resources': 'resources', 'tools': 'tools',
        'operations': 'ops', 'build': 'dist',
        **{f'runtime_{kind}': f'var/{kind}' for kind in ('data', 'state', 'cache', 'log', 'tmp', 'backups')},
    }
    return {kind: str(root / name) for kind, name in relative.items()}


def linked(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def children(path: Path, errors: list[str]) -> list[Path]:
    """Reject every reparse point before enumerating its target."""
    if not path.exists() and not path.is_symlink():
        return []
    if linked(path):
        errors.append(f'link/reparse point is outside managed traversal: {path}')
        return []
    if not path.is_dir():
        errors.append(f'expected directory: {path}')
        return []
    return list(path.iterdir())


def safe_tree(path: Path, errors: list[str]) -> None:
    for child in children(path, errors):
        if linked(child):
            errors.append(f'link/reparse point is outside managed traversal: {child}')
        elif child.is_dir():
            safe_tree(child, errors)


def check_report(root: Path, effort: str, phase: str, run: str | None = None,
                 today: date | None = None) -> dict:
    slug(effort)
    if phase == 'run-closed' and run is None:
        raise ValueError('run-closed requires --run')
    if run is not None:
        slug(run)
    if not root.is_dir():
        raise ValueError('project root must exist')
    today = today or date.today()
    errors: list[str] = []
    other_errors: list[str] = []
    def report():
        combined = errors + other_errors
        return {'ok': not combined, 'errors': combined, 'phase': phase,
                'scope': {'effort': effort, 'ok': not errors, 'errors': errors},
                'other_archives': {'ok': not other_errors, 'errors': other_errors}}
    # Check ancestors first so nested paths cannot traverse an external junction.
    for relative in ('.scratch', '.artifacts', '.artifacts/active', '.artifacts/archive'):
        path = root / relative
        if path.is_symlink() or path.exists() and linked(path):
            errors.append(f'link/reparse point is outside managed traversal: {path}')
            return report()
    task = root / '.scratch' / effort
    active = root / '.artifacts/active' / effort
    for child in children(task, errors):
        if child.name not in TASK_FILES and child.name != 'issues':
            errors.append(f'task output needs a fixed type/location: {child}')
        if child.name in TASK_FILES and not child.is_file():
            errors.append(f'expected task Markdown file: {child}')
        if child.name == 'issues':
            for ticket in children(child, errors):
                if not ticket.is_file() or ticket.suffix != '.md':
                    errors.append(f'expected one Markdown file per ticket: {ticket}')
    safe_tree(task, errors)
    for folder in children(active, errors):
        try:
            slug(folder.name)
        except ValueError:
            errors.append(f'invalid run directory: {folder}')
        for kind in children(folder, errors):
            if kind.name not in KINDS or not kind.is_dir():
                errors.append(f'run output needs a fixed kind directory: {kind}')
        safe_tree(folder, errors)
    if phase == 'closed':
        for path in (task, active):
            if path.exists() or path.is_symlink():
                errors.append(f'completed effort still occupies active location: {path}')
    elif phase == 'run-closed':
        target = active / str(run)
        if target.exists() or target.is_symlink():
            errors.append(f'finished run still occupies active location: {target}')
    # Scan only retention metadata, never historical bodies or credential contents.
    for archive in children(root / '.artifacts/archive', errors):
        archive_errors = errors if archive.name == effort else other_errors
        safe_tree(archive, archive_errors)
        if linked(archive) or not archive.is_dir():
            continue
        for archived_run in children(archive, archive_errors):
            if archived_run.name == 'retention.json':
                continue
            for kind in children(archived_run, archive_errors):
                if kind.name not in KINDS or kind.name in ('work', 'downloads') or not kind.is_dir():
                    archive_errors.append(f'temporary work/downloads cannot become archived evidence: {kind}')
        retention = archive / 'retention.json'
        if retention.is_symlink() or retention.exists() and linked(retention):
            archive_errors.append(f'linked retention metadata: {retention}')
            continue
        try:
            policy = json.loads(retention.read_text(encoding='utf-8'))
            if not isinstance(policy, dict) or not isinstance(policy.get('reason'), str) or not policy['reason'].strip():
                raise ValueError('a concrete retention reason is required')
            expires = date.fromisoformat(policy['expires_on'])
            if not today < expires <= today + timedelta(days=30):
                raise ValueError('retention has expired or exceeds 30 days')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            archive_errors.append(f'invalid retention metadata {retention}: {exc}')
    return report()


def check(root: Path, effort: str, phase: str, run: str | None = None,
          today: date | None = None) -> list[str]:
    """Keep the original list-returning interface for existing consumers."""
    return check_report(root, effort, phase, run, today)['errors']



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('paths', 'check'))
    parser.add_argument('--root', type=Path)
    parser.add_argument('--lifecycle-root', type=Path)
    parser.add_argument('--effort')
    parser.add_argument('--run')
    parser.add_argument('--phase', choices=('active', 'run-closed', 'closed'), default='active')
    args = parser.parse_args()
    try:
        if args.lifecycle_root is not None:
            if args.action != 'check' or args.root is not None or args.effort is not None:
                raise ValueError('lifecycle check cannot mix legacy arguments')
            # This read-only command must not create caches in the installed skill.
            previous_bytecode = sys.dont_write_bytecode
            try:
                sys.dont_write_bytecode = True
                import artifact_lifecycle
            finally:
                sys.dont_write_bytecode = previous_bytecode
            rows = artifact_lifecycle.sweep(args.lifecycle_root)
            ok = not any(v['status'] in {'error', 'changed', 'review-due'} for v in rows)
            print(json.dumps({'ok': ok, 'groups': rows}, ensure_ascii=False))
            return 0 if ok else 1
        if args.root is None or args.effort is None:
            raise ValueError('legacy check requires root and effort')
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('project root must be a directory')
        if args.action == 'paths':
            if args.run is None:
                raise ValueError('paths requires --run')
            result = {'ok': True, 'paths': paths(root, args.effort, args.run)}
        else:
            result = check_report(root, args.effort, args.phase, args.run)
    except (OSError, ValueError) as exc:
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
