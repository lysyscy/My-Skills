"""Opt-in artifact lifecycle. No scheduler, database access or recursive discovery.

Each --root is a dedicated, explicitly enrolled output area, never a project root.
All writers/readers must use `lease` around active consumption. check is read-only.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

VERSION = 1
PROTECTED = {'.git', '.env', 'data', 'source', 'src', 'backups', 'credentials'}

def stamp(value=None):
    if value is None:
        return datetime.now(timezone.utc)
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return result.astimezone(timezone.utc)

def safe(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if item.is_symlink() or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('linked/reparse path refused')
    return path

def atomic(path, data):
    temp = safe(path.with_suffix('.tmp'))
    with temp.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)

def enrolled(root):
    root = safe(root)
    config = json.loads(safe(root / '.lifecycle.json').read_text(encoding='utf-8'))
    if config != {'version': VERSION, 'root': str(root)}:
        raise ValueError('invalid enrollment')
    return root

def enroll(root):
    root = safe(root)
    if root.parent == root or root.name.lower() in PROTECTED:
        raise ValueError('protected root')
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError('enrollment requires an empty dedicated output directory')
    atomic(root / '.lifecycle.json', {'version': VERSION, 'root': str(root)})
    (root / '.lock').touch()
    (root / 'groups').mkdir()

@contextmanager
def lock(root):
    root = enrolled(root)
    with safe(root / '.lock').open('r+b') as stream:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield root
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)

def group(root, name):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', name):
        raise ValueError('invalid group id')
    folder = safe(root / 'groups' / name)
    return folder, safe(folder / 'record.json'), safe(folder / 'files')

def inventory(folder):
    result = {}
    for item in sorted(folder.iterdir()):
        safe(item)
        if item.is_dir():
            for key, value in inventory(item).items():
                result[item.name + '/' + key] = value
        elif item.is_file() and item.name.lower() not in PROTECTED:
            result[item.name] = hashlib.sha256(item.read_bytes()).hexdigest()
        else:
            raise ValueError('special or protected file refused')
    return result

def register(root, name, owner, reason, kind='evidence'):
    if kind not in {'evidence', 'work', 'permanent'} or not owner.strip() or not reason.strip():
        raise ValueError('owner, purpose and valid kind required')
    with lock(root) as root:
        folder, record, files = group(root, name)
        folder.mkdir()
        files.mkdir()
        atomic(record, dict(version=VERSION, id=name, owner=owner, reason=reason,
                            kind=kind, state='active', closed_at=None, expires_at=None,
                            hold=None, inventory=None))
        return str(files)

def load(root, name):
    folder, record, files = group(root, name)
    value = json.loads(record.read_text(encoding='utf-8'))
    if value.get('version') != VERSION or value.get('id') != name:
        raise ValueError('invalid group record')
    if value.get('kind') not in {'evidence', 'work', 'permanent'} or value.get('state') not in {'active', 'closed', 'deleting', 'deleted'}:
        raise ValueError('invalid kind/state')
    return record, files, value

def close(root, name, days=30, now=None, deadline=None):
    now = stamp(now)
    if days not in (30, 60):
        raise ValueError('supported retention is 30 or 60 days')
    with lock(root) as root:
        record, files, value = load(root, name)
        if value['state'] != 'active' or value['hold']:
            raise ValueError('close requires active, resolved group')
        value.update(state='closed', closed_at=now.isoformat(), inventory=inventory(files))
        value['expires_at'] = None if value['kind'] == 'permanent' else (now + timedelta(days=0 if value['kind'] == 'work' else days)).isoformat()
        if deadline is not None:
            if value['kind'] != 'evidence' or stamp(deadline) <= now:
                raise ValueError('explicit deadline requires evidence and future timestamp')
            value['expires_at'] = stamp(deadline).isoformat()
        value['days'] = days
        atomic(record, value)

def hold(root, name, reason, condition, now=None):
    now = stamp(now)
    if not reason.strip() or not condition.strip():
        raise ValueError('hold reason and release condition required')
    with lock(root) as root:
        record, files, value = load(root, name)
        if value['state'] not in {'active', 'closed'}:
            raise ValueError('cannot hold deletion already started')
        if value['hold']:
            raise ValueError('existing hold must be reviewed explicitly')
        value['hold'] = dict(reason=reason, condition=condition, review_at=(now + timedelta(days=30)).isoformat())
        atomic(record, value)

def review(root, name, reason, condition, now=None):
    now = stamp(now)
    if not reason.strip() or not condition.strip(): raise ValueError('review reason and condition required')
    with lock(root) as root:
        record, files, value = load(root, name)
        if not value['hold']: raise ValueError('no hold to review')
        value['hold'] = dict(reason=reason, condition=condition, review_at=(now + timedelta(days=30)).isoformat())
        atomic(record, value)

def release(root, name, now=None):
    now = stamp(now)
    with lock(root) as root:
        record, files, value = load(root, name)
        if not value['hold']:
            raise ValueError('no hold')
        value['hold'] = None
        if value['expires_at']:
            value['expires_at'] = max(stamp(value['expires_at']), now + timedelta(days=7)).isoformat()
        atomic(record, value)

def evaluate(value, files, now):
    if value['kind'] == 'permanent':
        return 'permanent'
    if value['hold']:
        return 'review-due' if now >= stamp(value['hold']['review_at']) else 'held'
    if value['state'] == 'active':
        return 'active'
    if value['state'] == 'deleted':
        return 'deleted'
    if not value['closed_at'] or not value['expires_at'] or not isinstance(value['inventory'], dict):
        raise ValueError('incomplete closure')
    actual = inventory(files)
    expected = value['inventory']
    if value['state'] == 'deleting':
        if any(expected.get(key) != digest for key, digest in actual.items()):
            return 'changed'
    elif actual != expected:
        return 'changed'
    return 'due' if now >= stamp(value['expires_at']) else 'retained'

def sweep(root, apply=False, now=None):
    now = stamp(now)
    results = []
    with lock(root) as root:
        for folder in sorted(safe(root / 'groups').iterdir()):
            try:
                record, files, value = load(root, folder.name)
                status = evaluate(value, files, now)
                if apply and status == 'deleted' and now >= stamp(value['deleted_at']) + timedelta(days=30):
                    if set(x.name for x in folder.iterdir()) != {'files', 'record.json'} or any(files.iterdir()):
                        raise ValueError('unexpected receipt contents')
                    files.rmdir()
                    record.unlink()
                    folder.rmdir()
                    results.append({'id': folder.name, 'status': 'receipt-expired'})
                    continue
                if apply and status == 'due':
                    value['state'] = 'deleting'
                    atomic(record, value)
                    # No recursive delete: remove only sealed members. Recheck each file.
                    for rel, digest in value['inventory'].items():
                        item = safe(files / rel)
                        if not item.is_relative_to(files) or '..' in Path(rel).parts:
                            raise ValueError('inventory path escape')
                        if item.exists():
                            if hashlib.sha256(item.read_bytes()).hexdigest() != digest:
                                raise ValueError('content changed during deletion')
                            item.unlink()
                    for item in sorted(files.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                        safe(item)
                        if item.is_dir():
                            item.rmdir()
                    if any(files.iterdir()):
                        raise ValueError('unexpected remaining content')
                    value.update(state='deleted', deleted_at=now.isoformat(), inventory={})
                    atomic(record, value)
                    status = 'deleted'
                results.append({'id': folder.name, 'status': status})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                results.append({'id': folder.name, 'status': 'error', 'error': str(exc)})
    return results

def notices(root, results):
    # Delivery is an adapter concern. Only emit newly actionable or changed events.
    with lock(root) as root:
        path = safe(root / '.notices.json')
        old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        current = {v['id']: v for v in results if v['status'] in {'error', 'changed', 'review-due'}}
        changed = [v for key,v in current.items() if old.get(key) != v]
        atomic(path, current)
        return changed

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['enroll','register','close','hold','review','release','check','sweep','lease'])
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--group')
    p.add_argument('--owner', default='')
    p.add_argument('--reason', default='')
    p.add_argument('--condition', default='')
    p.add_argument('--kind', default='evidence')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--deadline')
    a, command = p.parse_known_args()
    if command and a.action != 'lease': p.error('unexpected arguments')
    if a.action == 'enroll': result = enroll(a.root)
    elif a.action == 'register': result = register(a.root,a.group,a.owner,a.reason,a.kind)
    elif a.action == 'close': result = close(a.root,a.group,a.days,deadline=a.deadline)
    elif a.action == 'hold': result = hold(a.root,a.group,a.reason,a.condition)
    elif a.action == 'review': result = review(a.root,a.group,a.reason,a.condition)
    elif a.action == 'release': result = release(a.root,a.group)
    elif a.action == 'lease':
        command = command[1:] if command[:1] == ['--'] else command
        if not command: raise ValueError('lease requires command')
        with lock(a.root): return subprocess.run(command, check=False).returncode
    else: result = sweep(a.root, apply=a.action == 'sweep')
    if a.action == 'sweep':
        events = notices(a.root, result)
        print(json.dumps({'results': result, 'notifications': events}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 1 if isinstance(result,list) and any(r['status'] in {'error','changed','review-due'} for r in result) else 0

if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
