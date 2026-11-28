import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from setup_fixture import git, put


SKILL = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow'


def rule(path, *, category='source', owner='Fixture', apply=False):
    return dict(path=path, owner=owner, git_policy='tracked', manager='none',
                retention='fixture', exit_condition='fixture', apply_eligible=apply, **{'class': category})


class DirectoryGovernanceSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Fixture')
        git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        self.name = 'governance/custom-manifest.json'
        self.config = json.loads((SKILL / 'templates/directory-manifest.example.json').read_bytes())
        self.config['directories'].append(rule('governance'))
        self.write_manifest()
        git(self.root, 'add', self.name)
        git(self.root, 'commit', '-qm', 'Fixture baseline')

    def write_manifest(self):
        put(self.root, self.name, json.dumps(self.config))

    def audit(self, *args, code=0):
        output = subprocess.run(
            [sys.executable, '-B', '-X', 'utf8', str(SKILL / 'scripts/directory_audit.py'),
             '--root', str(self.root), '--manifest', self.name, *args],
            cwd=SKILL, capture_output=True, encoding='utf-8', check=False,
        )
        self.assertEqual(output.returncode, code, output.stdout + output.stderr)
        return output.stdout

    def test_apply_preserves_protected_ancestors_and_rechecks_at_index(self):
        protected = ('archive/child', 'business/child', 'docs/with-receipt/child')
        ordinary = 'retired-output'
        self.config['hard_protected'] = ['ARCHIVE']
        self.config['directories'] += [
            rule('archive'), rule('business', category='business'), rule('docs/with-receipt'),
            *(rule(name, category='residue', owner='none', apply=True) for name in protected),
        ]
        self.write_manifest()
        for name in (*protected, ordinary):
            (self.root / name).mkdir(parents=True)
        put(self.root, 'docs/with-receipt/run.json', '{}')
        preview = self.audit('--dry-run')
        self.assertIn(f'RESIDUE {ordinary}', preview)
        self.assertFalse(any(f'RESIDUE {name}' in preview for name in protected))
        self.assertTrue((self.root / ordinary).is_dir())
        put(self.root, f'{ordinary}/tracked.txt', 'tracked')
        git(self.root, 'add', f'{ordinary}/tracked.txt')
        (self.root / ordinary / 'tracked.txt').unlink()
        self.assertIn('Git', self.audit('--apply', code=1))
        self.assertTrue((self.root / ordinary).is_dir())
        git(self.root, 'rm', '--cached', '-qf', f'{ordinary}/tracked.txt')
        self.assertIn(f'REMOVED {ordinary}', self.audit('--apply'))
        self.assertFalse((self.root / ordinary).exists())
        self.assertTrue(all((self.root / name).is_dir() for name in protected))
        self.assertNotIn('REMOVED', self.audit('--apply'))

    def test_staged_uses_manifest_blob_and_accepts_agents(self):
        put(self.root, '.agents/skills/verify-sample/SKILL.md', '# Verify\n')
        put(self.root, 'unexpected/code.py', 'x = 1\n')
        git(self.root, 'add', '.agents', 'unexpected')
        output = self.audit('--staged', code=1)
        self.assertIn('ERROR unexpected', output)
        self.assertNotIn('ERROR .agents', output)
        self.config['directories'].append(rule('unexpected'))
        self.write_manifest()
        self.assertIn('ERROR unexpected', self.audit('--staged', code=1))
        git(self.root, 'add', self.name)
        self.assertIn('OK', self.audit('--staged'))

    def test_release_registry_uses_declared_directory_file_and_key(self):
        self.config['releases'] = dict(directory='deliveries', registry='governance/builds.json', key='builds')
        self.config['directories'] += [rule('deliveries'), rule('deliveries/known', category='residue',
                                                              owner='none', apply=True)]
        self.write_manifest()
        for name in ('known', 'unknown'):
            (self.root / 'deliveries' / name).mkdir(parents=True)
        put(self.root, 'governance/builds.json', '{"builds":{"known":{}}}')
        output = self.audit('--apply', code=1)
        self.assertIn('ERROR deliveries/unknown', output)
        self.assertNotIn('REMOVED', output)
        self.assertTrue((self.root / 'deliveries/known').is_dir())
