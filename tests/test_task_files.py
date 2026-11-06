"""Task closure reports actual files and consumers without runtime assumptions."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts/task_files.py'
spec = importlib.util.spec_from_file_location('task_files', SCRIPT)
task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task)


class TaskFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.put('.scratch/one/result.md', 'saved evidence')
        self.put('.scratch/tails/issues/T-1.md', 'done')
        self.put('.scratch/parallel/spec.md', 'active')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.revision = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, encoding='utf-8').stdout

    def put(self, name, body):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')
        return p

    def report(self, closed=False):
        return task.check_task(self.root, ['.scratch/one', '.scratch/tails/issues/T-1.md'],
                               self.revision, closed)

    def test_runtime_group_success_does_not_close_task_files(self):
        self.put('.artifacts/archive/other/broken.json', 'not relevant')
        report = self.report(True)
        self.assertFalse(report['ok'])
        self.assertEqual(len(report['files']), 2)
        self.assertIn('task material still occupies active paths', report['errors'])
        self.assertTrue((self.root/'.scratch/parallel/spec.md').exists())

    def test_saved_dirty_and_unique_inputs_are_distinguished_without_writes(self):
        self.put('.scratch/one/result.md', 'unique edit')
        self.put('.scratch/one/private.md', 'untracked unique')
        before = {str(p.relative_to(self.root)): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        report = self.report()
        rows = {x['path']: x for x in report['files']}
        self.assertTrue(rows['.scratch/one/result.md']['saved_in_revision'])
        self.assertFalse(rows['.scratch/one/result.md']['unchanged_from_revision'])
        self.assertFalse(rows['.scratch/one/private.md']['saved_in_revision'])
        after = {str(p.relative_to(self.root)): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_relative_links_and_code_references_block_exit_after_removal(self):
        self.put('docs/current.md', '[needed](../.scratch/one/result.md#fact)')
        self.put('reader.py', 'path = ".scratch/tails/issues/T-1.md"')
        self.git('add', '.')
        self.git('commit', '-qm', 'consumers')
        (self.root/'.scratch/one/result.md').unlink()
        (self.root/'.scratch/one').rmdir()
        (self.root/'.scratch/tails/issues/T-1.md').unlink()
        report = self.report(True)
        self.assertFalse(report['ok'])
        self.assertEqual({x['source'] for x in report['references']}, {'docs/current.md', 'reader.py'})
        self.put('docs/current.md', '[history](https://example.invalid/blob/abc/.scratch/one/result.md)')
        self.put('reader.py', 'path = "docs/current.md"')
        self.assertTrue(self.report(True)['ok'])

    def test_unreadable_reference_source_is_reported_as_incomplete(self):
        self.put('consumer.md', 'text').write_bytes(b'\xff\xfe\x00\x00')
        self.assertEqual(self.report()['unreadable'], ['consumer.md'])

    def test_unsafe_or_unknown_scope_is_not_a_successful_check(self):
        for scope in ['.scratch', '.scratch/../outside', 'C:/private', '.scratch/*']:
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                task.check_task(self.root, [scope])
        self.assertFalse(task.check_task(self.root, ['.scratch/typo'], closed=True)['ok'])

    def test_external_link_is_refused_before_reading_target(self):
        with tempfile.TemporaryDirectory() as outside:
            private = Path(outside)/'secret.md'
            private.write_text('untouched', encoding='utf-8')
            try:
                (self.root/'.scratch/one/link').symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(str(exc))
            with self.assertRaises(ValueError):
                self.report()
            self.assertEqual(private.read_text(encoding='utf-8'), 'untouched')

    def test_real_cli_fails_closed_material_and_does_not_create_cache(self):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--root', str(self.root),
                                 '--path', '.scratch/one', '--closed'],
                                capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
