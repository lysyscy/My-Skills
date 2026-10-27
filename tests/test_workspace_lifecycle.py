"""Workspace placement and closure use real isolated files; checks never mutate them."""
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts/workspace_check.py'
spec = importlib.util.spec_from_file_location('workspace_check', SCRIPT)
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workspace-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.today = date(2026, 10, 19)

    def put(self, name, body='fixture'):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')
        return p

    def check(self, phase='active', run=None):
        return workspace.check(self.root, 'example', phase, run, self.today)

    def archive(self, days=7, reason='Unique failure trace needed for diagnosis'):
        self.put('.artifacts/archive/example/r1/traces/trace.json')
        self.put('.artifacts/archive/example/retention.json', json.dumps({
            'reason': reason, 'expires_on': (self.today + timedelta(days=days)).isoformat(),
        }))

    def test_paths_share_one_task_and_run_namespace_without_creating_files(self):
        values = workspace.paths(self.root, 'example', 'r1')
        self.assertEqual(values['screenshots'], str(self.root/'.artifacts/active/example/r1/screenshots'))
        self.assertEqual(values['runtime_state'], str(self.root/'var/state'))
        self.assertEqual(values['fixtures'], str(self.root/'tests/fixtures'))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_path_escape_or_hidden_slug_is_rejected(self):
        for slug in ('../other', 'a/b', 'a\\b', '.', '..', '.hidden', 'a'*81):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                workspace.paths(self.root, slug, 'r1')

    def test_valid_active_task_and_output_categories(self):
        self.put('.scratch/example/spec.md')
        self.put('.scratch/example/issues/01-fixture.md')
        for kind in workspace.KINDS:
            self.put(f'.artifacts/active/example/r1/{kind}/fixture.txt')
        self.assertEqual(self.check(), [])

    def test_screenshot_or_script_in_scratch_is_rejected_without_deletion(self):
        for name in ('screen.png', 'helper.py', 'logs/trace.txt'):
            self.put('.scratch/example/'+name)
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(len(self.check()), 3)
        self.assertTrue(all(p.read_bytes() == value for p, value in before.items()))

    def test_loose_run_output_and_unknown_category_are_rejected(self):
        self.put('.artifacts/active/example/r1/log.txt')
        self.put('.artifacts/active/example/r1/misc/result.txt')
        self.assertEqual(len(self.check()), 2)

    def test_done_text_cannot_exempt_an_active_task(self):
        self.put('.scratch/example/spec.md', 'Status: completed\nEverything done; archive later.')
        self.assertTrue(any('completed effort' in error for error in self.check('closed')))

    def test_finished_run_cannot_keep_work_or_even_empty_active_directory(self):
        work = self.put('.artifacts/active/example/r1/work/helper.py')
        self.assertTrue(self.check('run-closed', 'r1'))
        work.unlink()
        work.parent.rmdir()
        self.assertTrue(self.check('run-closed', 'r1'))

    def test_phase_completion_keeps_other_runs_and_task(self):
        self.put('.scratch/example/spec.md', 'Status: active')
        self.put('.artifacts/active/example/r2/reports/result.json')
        self.assertEqual(self.check('run-closed', 'r1'), [])
        self.assertTrue(self.check('closed'))

    def test_closed_task_preserves_user_data_deliverables_and_other_efforts(self):
        names = ('data/source/original.xlsx', 'exports/customer/result.xlsx',
                 'var/data/database.sqlite', '.scratch/parallel/spec.md')
        for name in names:
            self.put(name)
        self.archive()
        self.assertEqual(self.check('closed'), [])
        self.assertTrue(all((self.root/name).is_file() for name in names))

    def test_archive_requires_reason_and_finite_unexpired_retention(self):
        for days, reason in ((0, 'diagnosis'), (-1, 'diagnosis'), (31, 'diagnosis'), (7, '')):
            with self.subTest(days=days, reason=reason):
                self.archive(days, reason)
                self.assertTrue(self.check('closed'))
        self.archive(30)
        self.assertEqual(self.check('closed'), [])
        (self.root/'.artifacts/archive/example/retention.json').unlink()
        self.assertTrue(self.check('closed'))

    def test_no_artifacts_needs_no_scaffold(self):
        self.assertEqual(self.check('closed'), [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_archiving_whole_work_copy_cannot_pass_as_selected_evidence(self):
        self.archive()
        self.put('.artifacts/archive/example/r1/work/source.py')
        self.assertTrue(any('temporary work' in e for e in self.check('closed')))

    def test_paths_cli_rejects_file_as_project_root(self):
        target = self.put('not-a-project')
        p = subprocess.run([sys.executable, str(SCRIPT), 'paths', '--root', str(target),
                            '--effort', 'example', '--run', 'r1'], capture_output=True,
                           text=True, encoding='utf-8', check=False)
        self.assertEqual(p.returncode, 1)

    def test_external_links_are_rejected_without_reading_or_modifying_target(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other)
            original = outside/'private.txt'
            original.write_text('private', encoding='utf-8')
            try:
                (self.root/'.artifacts').symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f'host cannot create link fixture: {exc}')
            self.assertTrue(any('link/reparse' in e for e in self.check('closed')))
            self.assertEqual(original.read_text(encoding='utf-8'), 'private')

    def test_real_cli_rejects_incomplete_closure(self):
        self.put('.scratch/example/spec.md', 'Status: completed')
        p = subprocess.run([sys.executable, str(SCRIPT), 'check', '--root', str(self.root),
                            '--effort', 'example', '--phase', 'closed'], capture_output=True,
                           text=True, encoding='utf-8', check=False)
        self.assertEqual(p.returncode, 1)
        self.assertFalse(json.loads(p.stdout)['ok'])

    def test_other_archive_issues_are_reported_without_failing_current_scope(self):
        self.put('.artifacts/archive/parallel/r1/work/helper.py')
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = workspace.check_report(self.root, 'example', 'closed', today=self.today)
        self.assertFalse(report['ok'])
        self.assertTrue(report['scope']['ok'])
        self.assertEqual(report['scope']['errors'], [])
        self.assertFalse(report['other_archives']['ok'])
        self.assertEqual(report['errors'], report['other_archives']['errors'])
        self.assertEqual(self.check('closed'), report['errors'])
        self.assertTrue(all(p.read_bytes() == body for p, body in before.items()))

    def test_current_archive_and_cli_keep_nonzero_overall_status(self):
        self.put('.artifacts/archive/example/r1/work/owned.py')
        self.put('.artifacts/archive/parallel/r1/work/other.py')
        p = subprocess.run([sys.executable, str(SCRIPT), 'check', '--root', str(self.root),
                            '--effort', 'example', '--phase', 'closed'], capture_output=True,
                           text=True, encoding='utf-8', check=False)
        self.assertEqual(p.returncode, 1)
        report = json.loads(p.stdout)
        self.assertFalse(report['ok'])
        self.assertFalse(report['scope']['ok'])
        self.assertFalse(report['other_archives']['ok'])
        self.assertTrue(all('/example/' in error.replace('\\', '/') for error in report['scope']['errors']))
        self.assertTrue(all('/parallel/' in error.replace('\\', '/') for error in report['other_archives']['errors']))
        self.assertEqual(report['errors'], report['scope']['errors'] + report['other_archives']['errors'])


if __name__ == '__main__':
    unittest.main()
