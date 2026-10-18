"""Source-only CLI verification must not require an installed Manager."""
import contextlib
import io
import json
import sys
from unittest.mock import patch

from test_skill_package import PackageFixture, git, manager


class SourceCliChecks(PackageFixture):
    def setUp(self):
        super().setUp()
        git(self.source, 'push', 'origin', 'main')
        self.runs = [{
            'head_sha': self.revision,
            'path': '.github/workflows/tests.yml',
            'event': 'push',
            'status': 'completed',
            'conclusion': 'success',
            'html_url': 'fixture',
        }]

    def run_cli(self, action='confirm-source'):
        argv = ['skill_package.py', action, '--source', str(self.source),
                '--revision', self.revision]
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), \
                patch.object(manager, 'github_runs', return_value=self.runs), \
                patch.object(manager, 'skills_manager_cli', side_effect=
                             manager.PackageError('Skills Manager CLI is unavailable')) as finder, \
                contextlib.redirect_stdout(output):
            status = manager.main()
        return status, json.loads(output.getvalue()), finder.call_count

    def test_source_cli_works_without_manager(self):
        status, result, lookups = self.run_cli()
        self.assertEqual(status, 0)
        self.assertEqual(result['status'], 'source_verified')
        self.assertEqual(result['source_revision'], self.revision)
        self.assertEqual(lookups, 0)

    def test_source_cli_still_requires_exact_successful_push_ci(self):
        good = dict(self.runs[0])
        for changes in ({'status': 'in_progress'}, {'conclusion': 'failure'},
                        {'head_sha': '0' * 40}, {'event': 'pull_request'},
                        {'path': '.github/workflows/other.yml'}):
            with self.subTest(changes=changes):
                self.runs[0] = dict(good, **changes)
                status, result, lookups = self.run_cli()
                self.assertEqual(status, 1)
                self.assertEqual(result['status'], 'blocked')
                self.assertIn('CI has not succeeded', result['error'])
                self.assertEqual(lookups, 0)

    def test_source_cli_still_rejects_dirty_source(self):
        self.write('skills/first/references/guide.md', 'Uncommitted change\n')
        status, result, lookups = self.run_cli()
        self.assertEqual(status, 1)
        self.assertIn('clean source', result['error'])
        self.assertEqual(lookups, 0)

    def test_manager_actions_still_require_manager(self):
        for action in ('preflight', 'confirm-install', 'confirm-distribution'):
            with self.subTest(action=action):
                status, result, lookups = self.run_cli(action)
                self.assertEqual(status, 1)
                self.assertEqual(result['error'], 'Skills Manager CLI is unavailable')
                self.assertEqual(lookups, 1)
