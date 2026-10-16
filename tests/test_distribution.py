"""Published source and portable backup must both be verifiable."""
from unittest.mock import patch
import json

from test_skill_package import PackageFixture, git, manager
from test_manager_sync import FakeManager


class DistributionChecks(PackageFixture):
    def setUp(self):
        super().setUp()
        git(self.source, 'push', 'origin', 'main')
        self.runs = [{'head_sha': self.revision, 'path': '.github/workflows/tests.yml',
                      'event': 'push', 'status': 'completed', 'conclusion': 'success', 'html_url': 'fixture'}]
        self.fake = FakeManager(self)
        self.fake.metadata = self.fake.library / '.skills-manager/skills'
        self.fake.metadata.mkdir(parents=True)
        for name in self.package.discover():
            self.fake.write_metadata(name)
        self.backup = self.home / 'backup.git'
        self.backup.mkdir()
        git(self.backup, 'init', '--bare', '--initial-branch=main')
        git(self.fake.library, 'init', '--initial-branch=main')
        git(self.fake.library, 'config', 'user.email', 'test@example.invalid')
        git(self.fake.library, 'config', 'user.name', 'Fixture')
        git(self.fake.library, 'remote', 'add', 'origin', str(self.backup))
        git(self.fake.library, 'add', '--all')
        git(self.fake.library, 'commit', '-m', 'portable skills')
        git(self.fake.library, 'push', 'origin', 'main')
        with patch.object(manager, 'manager_json', side_effect=self.fake):
            self.plan = self.package.preflight('fixture', self.revision)

    def query(self, cli, *args):
        if args == ('git', 'status'):
            return {'remote_url': str(self.backup), 'branch': 'main'}
        if args[:2] == ('skills', 'check'):
            return [{'name': args[2], 'update_status': 'up_to_date', 'last_check_error': None}]
        return self.fake(cli, *args)

    def confirm(self):
        with patch.object(manager, 'github_runs', return_value=self.runs), \
                patch.object(manager, 'manager_json', side_effect=self.query):
            return self.package.confirm_distribution('fixture', self.revision, self.plan)

    def test_complete_chain_has_source_ci_and_backup_receipts(self):
        result = self.confirm()
        self.assertEqual(result['status'], 'distribution_verified')
        self.assertEqual(result['source_revision'], self.revision)
        self.assertEqual(result['backup_revision'], git(self.backup, 'rev-parse', 'main'))

    def test_pending_failed_wrong_workflow_and_wrong_commit_ci_are_refused(self):
        for changes in ({'status': 'in_progress'}, {'conclusion': 'failure'},
                        {'head_sha': '0'*40}, {'path': '.github/workflows/other.yml'}):
            self.runs[0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(manager.PackageError):
                self.confirm()
            self.runs[0] = {'head_sha': self.revision, 'path': '.github/workflows/tests.yml',
                            'event': 'push', 'status': 'completed', 'conclusion': 'success'}

    def test_official_backup_without_revision_explicitly_requires_receiver_calibration(self):
        result = self.confirm()
        self.assertEqual(result['cross_device_detection'], 'needs_calibration_after_restore')
        self.assertIn('official Manager update', result['receiver_action'])

    def test_local_backup_without_remote_push_is_not_distribution(self):
        (self.fake.library/'backup-note.txt').write_text('new', encoding='utf-8')
        git(self.fake.library, 'add', 'backup-note.txt')
        git(self.fake.library, 'commit', '-m', 'not pushed')
        with self.assertRaisesRegex(manager.PackageError, 'backup remote'):
            self.confirm()

    def test_unknown_manager_detection_is_not_success(self):
        original = self.query
        def query(cli, *args):
            if args[:2] == ('skills', 'check'):
                return [{'name': args[2], 'update_status': 'unknown', 'last_check_error': None}]
            return original(cli, *args)
        with patch.object(manager, 'github_runs', return_value=self.runs), \
                patch.object(manager, 'manager_json', side_effect=query), \
                self.assertRaisesRegex(manager.PackageError, 'update detection'):
            self.package.confirm_distribution('fixture', self.revision, self.plan)

    def test_new_device_restores_files_and_exposes_missing_baseline(self):
        receiver = self.home / 'receiver'
        git(self.home, 'clone', str(self.backup), str(receiver))
        for name in self.package.discover():
            record = self.fake.record(name)
            metadata = json.loads((receiver/'.skills-manager/skills'/f'{record["id"]}.json').read_text())
            self.assertNotIn('revision', metadata['source'])
            self.assertEqual(manager.directory_fingerprint(receiver/name),
                             self.package.committed_fingerprint(self.revision, name))

    def test_ignored_skill_resource_cannot_pass_a_clean_pushed_backup(self):
        library = self.fake.library
        (library/'.gitignore').write_text('first/references/guide.md\n', encoding='utf-8')
        git(library, 'rm', '--cached', 'first/references/guide.md')
        git(library, 'add', '.gitignore')
        git(library, 'commit', '-m', 'omit required resource')
        git(library, 'push', 'origin', 'main')
        with self.assertRaisesRegex(manager.PackageError, 'backup omits'):
            self.confirm()
