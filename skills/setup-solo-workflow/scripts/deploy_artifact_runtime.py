"""Deploy a verified setup artifact runtime into one explicitly selected project.

Default is a read-only plan. The caller verifies the source revision through the
package release workflow; the deployed manifest binds that revision to exact bytes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SOURCE = Path(__file__).with_name('artifact_lifecycle.py')
RELATIVE = Path('tools/_vendor/setup_solo_workflow')


def runtime():
    spec = importlib.util.spec_from_file_location('setup_artifact_runtime', SOURCE)
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def write_bytes(path, data):
    with tempfile.NamedTemporaryFile(prefix='setup-', suffix='.tmp', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def deploy(project, revision, *, apply=False):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('a verified full source commit is required')
    module = runtime()
    project = module.safe(project)
    if not project.is_dir():
        raise ValueError('project directory does not exist')
    target = module.safe(project / RELATIVE)
    code = module.safe(target / SOURCE.name)
    manifest_path = module.safe(target / 'deployment.json')
    output = module.safe(project / '.artifacts/runs')
    content = SOURCE.read_bytes()
    ast.parse(content.decode('utf-8'))
    digest = hashlib.sha256(content).hexdigest()
    manifest = dict(version=1, source='lysyscy/My-Skills:skills/setup-solo-workflow/scripts',
                    revision=revision, files={SOURCE.name: digest})
    previous = None
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        if (previous.get('version') != 1 or previous.get('source') != manifest['source'] or
                set(previous.get('files', {})) != {SOURCE.name}):
            raise ValueError('runtime deployment ownership is unknown')
    if target.exists():
        unknown = [p.name for p in target.iterdir()
                   if p.name not in {SOURCE.name, 'deployment.json', '__pycache__'}]
        if unknown:
            raise ValueError('unowned runtime files: ' + ', '.join(sorted(unknown)))
        if (target / '__pycache__').exists():
            module.safe(target / '__pycache__')
    if code.exists():
        if previous is None:
            raise ValueError('existing runtime is not owned by setup')
        actual = hashlib.sha256(code.read_bytes()).hexdigest()
        if actual not in {previous['files'][SOURCE.name], digest}:
            raise ValueError('local runtime edits must be preserved before deployment')
    elif previous is not None:
        raise ValueError('owned runtime is missing; investigate before updating')
    if output.exists():
        config = module.configuration(output)
        if config.get('layout') != 'runs' or not Path(config['project']).samefile(project):
            raise ValueError('project output area belongs to another configuration')
    changed = previous != manifest or not code.exists()
    result = dict(status='planned', project=str(project), runtime=str(code),
                  output=str(output), revision=revision, changed=changed,
                  output_enrolled=output.exists())
    if not apply:
        return result
    target.mkdir(parents=True, exist_ok=True)
    if not code.exists() or code.read_bytes() != content:
        write_bytes(code, content)
    encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if previous != manifest:
        write_bytes(manifest_path, encoded)
    if not output.exists():
        module.enroll(output, project=project)
    if code.read_bytes() != content or json.loads(manifest_path.read_text(encoding='utf-8')) != manifest:
        raise RuntimeError('runtime deployment readback failed')
    module.configuration(output)
    result.update(status='deployed', output_enrolled=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    print(json.dumps(deploy(args.project, args.revision, apply=args.apply), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
