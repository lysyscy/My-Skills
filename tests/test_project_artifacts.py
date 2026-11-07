import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


m = module('artifact_lifecycle')
installer = module('deploy_artifact_runtime')


class ProjectArtifactsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.root = self.project / '.artifacts/runs'
        m.enroll(self.root, project=self.project)
        self.now = datetime(2026, 11, 6, tzinfo=timezone.utc)

    def at(self, days):
        return (self.now + timedelta(days=days)).isoformat()

    def add(self, development=True):
        files = Path(m.register(self.root, 'one', 'test', 'synthetic development',
                                development=development, workspace=self.project))
        (files / 'reports').mkdir()
        (files / 'reports/result.txt').write_text('evidence', encoding='utf-8')
        return files

    def ended_producer(self):
        record, _, value = m.load(self.root, 'one')
        value['producer']['start'] = 'earlier-process-incarnation'
        m.atomic(record, value)

    def test_direct_layout_failure_retention_and_metadata_expiration(self):
        files = self.add()
        self.assertEqual(files, self.root / 'one')
        self.assertTrue((files / 'run.json').is_file())
        m.close(self.root, 'one', now=self.at(0), result='failure')
        value = m.load(self.root, 'one')[2]
        self.assertEqual(value['operation_result'], 'failure')
        self.assertNotIn('run.json', value['inventory'])
        self.assertEqual(m.sweep(self.root, True, self.at(29))[0]['status'], 'retained')
        self.assertEqual(m.sweep(self.root, True, self.at(30))[0]['status'], 'deleted')
        self.assertTrue((files / 'run.json').exists())
        self.assertEqual(m.sweep(self.root, True, self.at(60))[0]['status'], 'receipt-expired')
        self.assertFalse(files.exists())

    def test_abandoned_development_starts_clock_when_observed(self):
        files = self.add()
        self.ended_producer()
        before = (files / 'run.json').read_bytes()
        self.assertEqual(m.sweep(self.root, now=self.at(10))[0]['status'], 'abandoned-ready')
        self.assertEqual((files / 'run.json').read_bytes(), before)
        self.assertEqual(m.sweep(self.root, True, self.at(10))[0]['status'], 'abandoned-closed')
        self.assertEqual(m.load(self.root, 'one')[2]['expires_at'], self.at(40))
        self.assertEqual(m.sweep(self.root, True, self.at(39))[0]['status'], 'retained')
        self.assertEqual(m.sweep(self.root, True, self.at(40))[0]['status'], 'deleted')

    def test_unknown_and_explicitly_protected_runs_stay_active(self):
        self.add(development=False)
        self.assertEqual(m.sweep(self.root, True, self.at(100))[0]['status'], 'active')
        record, _, value = m.load(self.root, 'one')
        value.update(development=True, producer={'pid': 1})
        m.atomic(record, value)
        self.assertEqual(m.sweep(self.root, True, self.at(100))[0]['status'], 'activity-unknown')
        m.hold(self.root, 'one', 'unique input', 'owner confirmation', now=self.at(100))
        self.assertEqual(m.sweep(self.root, True, self.at(101))[0]['status'], 'held')

    def test_live_child_consumer_protects_abandoned_parent(self):
        self.add()
        self.ended_producer()
        script = '''import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('runtime',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with m.consume(Path(sys.argv[2]),'one'):
    print('ready',flush=True)
    sys.stdin.readline()
'''
        child = subprocess.Popen([sys.executable, '-B', '-c', script,
                                  str(SCRIPTS / 'artifact_lifecycle.py'), str(self.root)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding='utf-8')
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            self.assertEqual(m.sweep(self.root, True, self.at(10))[0]['status'], 'busy')
            with self.assertRaisesRegex(ValueError, 'consumer'):
                m.close(self.root, 'one')
            _, errors = child.communicate('\n', timeout=15)
            self.assertEqual(child.returncode, 0, errors)
        finally:
            if child.poll() is None:
                child.kill(); child.communicate()
        self.assertEqual(m.sweep(self.root, True, self.at(10))[0]['status'], 'abandoned-closed')

    def test_nested_consumers_do_not_release_outer_protection(self):
        self.add()
        with m.consume(self.root, 'one'):
            with m.consume(self.root, 'one'):
                self.assertEqual(m.load(self.root, 'one')[2]['consumers'][0]['count'], 2)
            self.assertEqual(m.sweep(self.root, True, self.at(10))[0]['status'], 'busy')
        self.assertEqual(m.load(self.root, 'one')[2]['consumers'], [])

    def test_closed_evidence_reader_prevents_expiry_without_renewing(self):
        self.add(); m.close(self.root, 'one', now=self.at(0))
        with m.consume(self.root, 'one', writing=False):
            self.assertEqual(m.sweep(self.root, True, self.at(40))[0]['status'], 'busy')
        self.assertEqual(m.load(self.root, 'one')[2]['expires_at'], self.at(30))
        self.assertEqual(m.sweep(self.root, True, self.at(40))[0]['status'], 'deleted')

    def test_added_content_and_partial_delete_remain_protected(self):
        files = self.add(); m.close(self.root, 'one', now=self.at(0))
        original = Path.unlink
        def occupied(path, *args, **kwargs):
            if path.name == 'result.txt':
                raise PermissionError('synthetic occupied file')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', occupied):
            self.assertEqual(m.sweep(self.root, True, self.at(30))[0]['status'], 'error')
        (files / 'unique.txt').write_text('unregistered', encoding='utf-8')
        self.assertEqual(m.sweep(self.root, True, self.at(31))[0]['status'], 'changed')
        self.assertEqual((files / 'unique.txt').read_text(), 'unregistered')

    def test_project_copy_is_not_silently_reenrolled(self):
        config = self.root / '.lifecycle.json'
        data = json.loads(config.read_text())
        data['root'] = str(self.project / 'another-output')
        config.write_text(json.dumps(data))
        with self.assertRaises((OSError, ValueError)):
            m.enrolled(self.root)


class RuntimeDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.revision = 'a' * 40

    def test_dry_run_and_idempotent_deployment_work_without_personal_install(self):
        plan = installer.deploy(self.project, self.revision)
        self.assertEqual(list(self.project.iterdir()), [])
        result = installer.deploy(self.project, self.revision, apply=True)
        self.assertEqual(result['status'], 'deployed')
        deployed = Path(result['runtime'])
        self.assertEqual(deployed.read_bytes(), installer.SOURCE.read_bytes())
        before = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        self.assertFalse(installer.deploy(self.project, self.revision, apply=True)['changed'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})
        command = subprocess.run([sys.executable, '-B', str(deployed), 'check', '--root', result['output']],
                                 cwd=self.project, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertEqual(json.loads(command.stdout), [])

    def test_local_edits_and_unowned_files_are_not_overwritten(self):
        result = installer.deploy(self.project, self.revision, apply=True)
        deployed = Path(result['runtime'])
        deployed.write_text('unique local implementation', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'local runtime edits'):
            installer.deploy(self.project, 'b' * 40, apply=True)
        self.assertEqual(deployed.read_text(), 'unique local implementation')

    def test_upgrade_adds_adapter_but_protects_unowned_adapter(self):
        with patch.object(installer, 'SOURCES', (installer.SOURCE,)):
            result = installer.deploy(self.project, self.revision, apply=True)
        target = self.project / installer.RELATIVE / 'impeccable_artifacts.py'
        target.write_text('unique', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'not owned'):
            installer.deploy(self.project, 'b' * 40, apply=True)
        self.assertEqual(target.read_text(), 'unique')
        target.unlink()  # synthetic test-only file
        installer.deploy(self.project, 'b' * 40, apply=True)
        self.assertEqual(target.read_bytes(), installer.SOURCE.with_name(target.name).read_bytes())
        self.assertFalse(installer.deploy(self.project, 'b' * 40)['changed'])

    def test_existing_unregistered_output_is_not_adopted(self):
        output = self.project / '.artifacts/runs'
        output.mkdir(parents=True)
        (output / 'business.txt').write_text('original', encoding='utf-8')
        with self.assertRaises((OSError, ValueError)):
            installer.deploy(self.project, self.revision, apply=True)
        self.assertFalse((self.project / installer.RELATIVE).exists())
        self.assertEqual((output / 'business.txt').read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
