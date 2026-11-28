import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from setup_fixture import git, put


SKILL = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow'
SCRIPTS = SKILL / 'scripts'
TASK = """---
id: setup-project
kind: ticket
status: open
parent: null
children: []
blocked_by: []
worktree: null
worktree_state: null
managed_runs: []
remaining_acceptance: ["Run one user path"]
next_step: Review the fixture
updated_at: 2026-01-01T12:00:00+00:00
---
# Set up project
"""


class DocOpsSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.workspace = Path(tmp.name).resolve()
        self.repo = self.workspace / 'sample checkout'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'config', 'user.name', 'Fixture')
        git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        self.config_path = self.repo / 'doc-ops.json'
        self.config = json.loads((SKILL / 'templates/doc-ops.config.example.json').read_bytes())
        self.config['git']['worktree_root'] = '../checkouts'
        self.write_config()
        self.entrypoint = SCRIPTS / 'doc_ops.py'
        put(self.repo, 'docs/status.md', '# Status\n\n' + self.config['entry']['view_start'] + '\n'
            + self.config['entry']['view_end'] + '\n\n## Maintained by hand\n\nKeep this section.\n')
        put(self.repo, 'docs/tasks/setup-project.md', TASK)
        put(self.repo, '.gitignore', '/.artifacts/\n/preview/\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'Fixture baseline')

    def write_config(self):
        self.config_path.write_text(json.dumps(self.config), encoding='utf-8')

    def python(self, script, *arguments, code=0):
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', str(script), *map(str, arguments)],
            cwd=self.workspace, capture_output=True, encoding='utf-8', check=False,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def doc_ops(self, command, *args, code=0):
        return self.python(self.entrypoint, command, '--root', self.repo, '--config', self.config_path,
                           *args, code=code)

    def remote(self):
        origin = self.workspace / 'remote.git'
        git(self.workspace, 'init', '-q', '--bare', str(origin))
        git(self.repo, 'remote', 'add', 'origin', str(origin))
        git(self.repo, 'push', '-q', 'origin', 'main')
        return origin

    def declare_tree(self):
        self.remote()
        path = self.workspace / 'checkouts' / 'feature'
        git(self.repo, 'worktree', 'add', '-qb', 'feature', str(path))
        git(self.repo, 'push', '-q', 'origin', 'feature')
        self.config['closeout']['worktrees'] = [dict(
            id='feature', state='retiring', branch='feature', label='Feature', reason='Merged',
            head=git(path, 'rev-parse', 'HEAD'), consumers_checked=True, thread_bindings=[],
        )]
        self.write_config()
        return path

    def test_release_free_view_refresh_and_install_are_repeatable(self):
        deployer = SCRIPTS / 'deploy_workflow_tools.py'
        args = ['--project', self.repo, '--revision', 'a' * 40, '--module', 'doc-ops']
        self.assertTrue(self.python(deployer, *args)['changed'])
        self.assertFalse((self.repo / 'tools').exists())
        self.assertTrue(self.python(deployer, *args, '--apply')['changed'])
        self.assertFalse(self.python(deployer, *args, '--apply')['changed'])
        self.entrypoint = self.repo / 'tools/audit/doc_ops.py'
        self.assertFalse((self.repo / 'tools/audit/directory_audit.py').exists())
        self.assertEqual(self.doc_ops('check', code=1)['diagnostics'][0]['code'], 'ACTIVE_VIEW_DRIFT')
        report = self.doc_ops('refresh')
        self.assertEqual((report['task_count'], report['release_count'], report['changed']), (1, 0, True))
        status = (self.repo / 'docs/status.md').read_text(encoding='utf-8')
        self.assertIn('[Set up project](tasks/setup-project.md)', status)
        self.assertIn('Keep this section.', status)
        self.assertFalse(self.doc_ops('refresh')['changed'])
        self.assertTrue(self.doc_ops('check')['ok'])
        self.assertFalse((self.entrypoint.parent / 'doc_ops/__pycache__').exists())
        self.entrypoint.write_text('unique local edits', encoding='utf-8')
        refused = subprocess.run(
            [sys.executable, str(deployer), *map(str, args), '--apply'],
            cwd=self.workspace, capture_output=True, encoding='utf-8', check=False,
        )
        self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
        self.assertIn('preserve local edits', refused.stderr)
        self.assertEqual(self.entrypoint.read_text(encoding='utf-8'), 'unique local edits')

    def test_links_catch_tracked_to_untracked(self):
        put(self.repo, 'docs/tasks/setup-project.md', TASK + '\n[Local draft](draft.md)\n')
        put(self.repo, 'docs/tasks/draft.md', '# Draft\n')
        report = self.doc_ops('links', code=1)
        self.assertEqual([(entry['code'], entry['target']) for entry in report['diagnostics']],
                         [('LINK_UNTRACKED_TARGET', 'docs/tasks/draft.md')])
        git(self.repo, 'add', 'docs/tasks/draft.md')
        self.assertTrue(self.doc_ops('links')['ok'])

    def test_configured_release_table_can_distinguish_same_commit_receipts(self):
        entry = self.config['entry']
        entry.update(release_sources=[{'glob': '.artifacts/*/receipt.json', 'run_id_parent': 0}],
                     release_verified={'loaded': True}, release_fields=dict(
                         action='action', product_commit='commit', pid='listener.pid', finished_at='finished',
                     ), release_actions=['restart'], release_limit=2, release_heading='## Releases',
                     release_history_note='Older receipts stay with the deployment owner.', utc_offset_minutes=0)
        self.write_config()
        path = self.repo / 'docs/status.md'
        path.write_text(path.read_text(encoding='utf-8').replace(self.config['entry']['view_start'],
                        '## Releases\n\nPrevious contents\n\n' + entry['view_start']), encoding='utf-8')
        for ordinal in (1, 2):
            put(self.repo, f'.artifacts/run-{ordinal}/receipt.json', json.dumps({
                'loaded': True, 'action': 'restart', 'commit': 'b' * 40,
                'listener': {'pid': 100 + ordinal}, 'finished': f'2026-01-0{ordinal}T00:00:00+00:00',
            }))
        self.assertEqual(self.doc_ops('refresh')['release_count'], 2)
        status = path.read_text(encoding='utf-8')
        self.assertLess(status.index('`run-2`'), status.index('`run-1`'))
        self.assertIn('| 102 |', status)
        self.assertTrue(self.doc_ops('check')['ok'])

    def test_preview_source_and_legacy_fallback_block_retirement(self):
        path = self.declare_tree()
        self.config['closeout']['preview_registries'] = ['preview/current.json']
        self.write_config()
        process = {'pid': 19, 'created': 'fixture'}
        owner = self.repo / 'preview/owner.json'
        current = 'preview/current.json'
        put(self.repo, 'preview/owner.json', json.dumps({'source_root': str(path), 'process': process}))
        for record, expected in (
            ({'source_root': str(path), 'owner_path': str(self.repo)}, 'WORKTREE_PREVIEW_REGISTERED'),
            ({'owner_path': str(owner), 'process': process}, 'WORKTREE_PREVIEW_REGISTERED'),
            ({'owner_path': str(owner), 'process': {'pid': 20}}, 'WORKTREE_PREVIEW_SOURCE_UNCONFIRMED'),
            ({'owner_path': 'relative/receipt.json'}, 'WORKTREE_PREVIEW_SOURCE_UNCONFIRMED'),
        ):
            with self.subTest(record=record):
                put(self.repo, current, json.dumps(record))
                plan = self.doc_ops('closeout-plan')
                self.assertEqual(plan['actions'], [])
                self.assertIn(expected, plan['blocked'][0]['reasons'])
        put(self.repo, current, json.dumps({'source_root': str(self.repo), 'owner_path': str(path)}))
        self.assertEqual(self.doc_ops('closeout-plan')['actions'][0]['kind'], 'retire_worktree')

    def test_closeout_stale_plan_apply_and_idempotency_without_releases(self):
        path = self.declare_tree()
        first = self.workspace / 'first.json'
        self.assertEqual(self.doc_ops('closeout-plan', '--out', first)['actions'][0]['kind'], 'retire_worktree')
        detail = path / 'unsaved.txt'
        detail.write_text('fixture', encoding='utf-8')
        refused = self.doc_ops('closeout-apply', '--plan', first, code=1)
        self.assertEqual(refused['diagnostics'][0]['code'], 'PLAN_STALE')
        self.assertEqual(detail.read_text(encoding='utf-8'), 'fixture')
        detail.unlink()
        applied = self.doc_ops('closeout-apply', '--plan', first)
        self.assertEqual(applied['applied'][0]['id'], 'feature')
        self.assertFalse(path.exists())
        self.assertEqual(git(self.repo, 'branch', '--list', 'feature'), '')
        self.assertEqual(git(self.repo, 'ls-remote', 'origin', 'refs/heads/feature'), '')
        second = self.workspace / 'second.json'
        self.assertEqual(self.doc_ops('closeout-plan', '--out', second)['actions'], [])
        self.assertEqual(self.doc_ops('closeout-apply', '--plan', second)['applied'], [])

    def test_configured_project_runtime_and_install_sibling_can_close_real_group(self):
        self.remote()
        copied_runtime = self.repo / 'project tools/session_lifecycle.py'
        copied_runtime.parent.mkdir()
        shutil.copyfile(SCRIPTS / 'artifact_lifecycle.py', copied_runtime)
        area = self.repo / '.artifacts/session-runs'
        self.python(copied_runtime, 'enroll', '--root', area, '--project', self.repo)
        for name, settings in (
            ('project-runtime', {'runtime': 'project tools/session_lifecycle.py'}),
            ('sibling-runtime', {}),
        ):
            with self.subTest(name=name):
                self.python(copied_runtime, 'register', '--root', area, '--group', name,
                            '--kind', 'work', '--owner', 'fixture', '--reason', 'temporary render')
                put(area, f'{name}/render.txt', 'Temporary')
                self.config['closeout']['runs'] = dict(
                    **settings, root='.artifacts/session-runs', retention_days=30,
                    release=[dict(id=name, owner='fixture', kind='work', released_on='2000-01-01',
                                  reason='Fixture finished')],
                )
                self.write_config()
                plan = self.workspace / f'{name}.json'
                self.assertEqual(self.doc_ops('closeout-plan', '--out', plan)['actions'][0]['id'], name)
                self.doc_ops('closeout-apply', '--plan', plan)
                self.assertFalse((area / name / 'render.txt').exists())
                self.assertEqual(json.loads((area / name / 'run.json').read_bytes())['state'], 'deleted')
                self.assertEqual(self.doc_ops('closeout-plan')['actions'], [])
