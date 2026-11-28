"""Plan or deploy the selected workflow tools at a verified source revision."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

SOURCE = Path(__file__).resolve().parent
MODULES = {
    'doc-ops': ('doc_ops.py', *(f'doc_ops/{name}.py' for name in (
        '__init__', 'closeout', 'links', 'processes', 'releases', 'repo', 'tasks',
    ))),
    'directory-governance': ('directory_audit.py',),
    'code-guardrails': ('comment_guard.py',),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def existing(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def deploy(project: Path, revision: str, modules: list[str], *, apply: bool = False) -> dict:
    from deploy_artifact_runtime import runtime, write_bytes

    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('a verified full source commit is required')
    safe = runtime().safe
    project = safe(project)
    if not project.is_dir():
        raise ValueError('project directory does not exist')
    target = safe(project / 'tools/audit')
    updates = {}
    for module in sorted(set(modules)):
        names = MODULES[module]
        manifest_path = safe(target / f'.setup-{module}.json')
        previous_bytes = existing(manifest_path)
        previous = json.loads(previous_bytes) if previous_bytes is not None else None
        contents = {name: (SOURCE / name).read_bytes() for name in names}
        for data in contents.values():
            ast.parse(data)
        hashes = {name: digest(data) for name, data in contents.items()}
        manifest = dict(schema=1, module=module, source='lysyscy/My-Skills:skills/setup-solo-workflow/scripts',
                        revision=revision, files=hashes)
        if previous_bytes is not None and (
            not isinstance(previous, dict) or previous.get('schema') != manifest['schema']
            or previous.get('source') != manifest['source'] or previous.get('module') != module
            or not isinstance(previous.get('files'), dict) or not previous['files'].keys() <= hashes.keys()
        ):
            raise ValueError(f'unknown deployment ownership: {manifest_path}')
        old_hashes = previous['files'] if previous else {}
        for name, data in contents.items():
            path = safe(target / name)
            actual_bytes = existing(path)
            if actual_bytes is not None:
                actual = digest(actual_bytes)
                if actual not in {old_hashes.get(name), hashes[name]}:
                    raise ValueError(f'preserve local edits before deploying: {path}')
                if actual == hashes[name]:
                    continue
            elif name in old_hashes:
                raise ValueError(f'owned tool file is missing: {path}')
            updates[path] = (actual_bytes, data)
        if previous != manifest:
            updates[manifest_path] = (previous_bytes, (json.dumps(manifest, indent=2) + '\n').encode())
    if apply:
        for path, (before, data) in updates.items():
            safe(path.parent).mkdir(parents=True, exist_ok=True)
            actual = existing(safe(path))
            if actual == data:
                continue
            if actual != before:
                raise ValueError(f'tool changed during deployment: {path}')
            write_bytes(path, data)
        if any(path.read_bytes() != data for path, (_, data) in updates.items()):
            raise RuntimeError('workflow tool deployment readback failed')
    return dict(status='deployed' if apply else 'planned', changed=bool(updates), target=str(target),
                files=[path.relative_to(project).as_posix() for path in updates])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--module', choices=sorted(MODULES), action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = deploy(args.project, args.revision, args.module, apply=args.apply)
    except (OSError, ValueError, RuntimeError, SyntaxError) as error:
        print(json.dumps(dict(status='failed', error=str(error))), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
