import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
import smyw_artifacts as adapter

life = adapter.life
NODE = shutil.which('node')

BUILD = '''import fs from 'node:fs'; import path from 'node:path';
const spec=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
fs.writeFileSync(path.join(path.dirname(process.argv[2]),'preview.html'),spec.title);
'''
APPLY = '''import fs from 'node:fs'; import path from 'node:path';
const input=process.argv[2], target=process.argv[3];
const patch=JSON.parse(fs.readFileSync(input,'utf8').split('```json\\n')[1].split('\\n```')[0]);
const spec=JSON.parse(fs.readFileSync(target,'utf8'));
if(patch.base!==spec.version) process.exit(3);
if(process.argv.includes('--dry-run')) process.exit(0);
fs.copyFileSync(target,path.join(path.dirname(target),'spec-v'+spec.version+'.json'));
spec.title=patch.ops[0].set.title;spec.version++;
fs.writeFileSync(target,JSON.stringify(spec));
'''


@unittest.skipUnless(NODE, 'Node is required to exercise the smyw contract')
class SmywArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        self.project.mkdir()
        self.root = self.project / '.artifacts/runs'
        life.enroll(self.root, project=self.project)
        self.skill = Path(self.temp.name) / 'upstream-smyw'
        (self.skill / 'scripts').mkdir(parents=True)
        (self.skill / 'SKILL.md').write_text('synthetic', encoding='utf-8')
        (self.skill / 'scripts/build.mjs').write_text(BUILD, encoding='utf-8')
        (self.skill / 'scripts/apply-feedback.mjs').write_text(APPLY, encoding='utf-8')

    def start(self):
        result = adapter.start(self.project, 'trial', 'test', self.skill, NODE)
        self.directory = Path(result['directory'])
        self.spec = self.directory / 'spec.json'
        self.spec.write_text(json.dumps({'title': 'original', 'version': 1}), encoding='utf-8')

    def write_feedback(self):
        patch = {'format': 'smyw-patch@1', 'base': 1,
                 'ops': [{'op': 'top', 'set': {'title': 'revised'}}]}
        (self.directory / 'feedback-v1.md').write_text('```json\n' + json.dumps(patch) + '\n```\n', encoding='utf-8', newline='\n')

    def test_build_feedback_and_close_while_preserving_unmanaged_files(self):
        legacy = self.project / '.smyw/old/preview.html'
        legacy.parent.mkdir(parents=True); legacy.write_text('do not adopt', encoding='utf-8')
        self.start(); self.write_feedback()
        self.assertEqual(adapter.invoke(self.project, 'trial', self.skill, 'build', node=NODE), 0)
        self.assertEqual((self.directory / 'preview.html').read_text(encoding='utf-8'), 'original')
        before = self.spec.read_bytes()
        self.assertEqual(adapter.invoke(self.project, 'trial', self.skill, 'apply', feedback='feedback-v1.md', node=NODE, dry_run=True), 0)
        self.assertEqual(self.spec.read_bytes(), before)
        self.assertEqual(adapter.invoke(self.project, 'trial', self.skill, 'apply', feedback='feedback-v1.md', node=NODE), 0)
        self.assertEqual(json.loads(self.spec.read_text(encoding='utf-8'))['title'], 'revised')
        self.assertTrue((self.directory / 'spec-v1.json').is_file())
        with self.assertRaisesRegex(ValueError, 'confirmation'):
            adapter.finish(self.project, 'trial')
        with life.consume(self.root, 'trial'):
            with self.assertRaisesRegex(ValueError, 'consumer'):
                adapter.finish(self.project, 'trial', confirmed=True)
        self.assertEqual(life.load(self.root, 'trial')[2]['state'], 'active')
        adapter.finish(self.project, 'trial', confirmed=True)
        state = life.load(self.root, 'trial')[2]
        self.assertEqual(state['kind'], 'work')
        self.assertEqual(life.sweep(self.root, True, state['expires_at'])[0]['status'], 'deleted')
        self.assertEqual(legacy.read_text(encoding='utf-8'), 'do not adopt')

    def test_updated_upstream_is_rechecked_and_incompatible_update_preserves_draft(self):
        self.start(); before = self.spec.read_bytes()
        build = self.skill / 'scripts/build.mjs'
        build.write_text('process.exit(0);', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'contract changed'):
            adapter.invoke(self.project, 'trial', self.skill, 'build', node=NODE)
        self.assertEqual(self.spec.read_bytes(), before)
        self.assertEqual(life.load(self.root, 'trial')[2]['state'], 'active')
        build.write_text(BUILD + "\nfs.writeFileSync('extra.txt','relative output');\n", encoding='utf-8')
        self.assertEqual(adapter.invoke(self.project, 'trial', self.skill, 'build', node=NODE), 0)
        self.assertTrue((self.directory / 'preview.html').exists())
        self.assertTrue((self.directory / 'extra.txt').exists())
        self.assertFalse((self.project / 'extra.txt').exists())

    def test_bad_feedback_path_and_bad_upstream_cannot_touch_project(self):
        self.start()
        outside = self.project / 'outside.md'; outside.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'inside'):
            adapter.invoke(self.project, 'trial', self.skill, 'apply', feedback='../../../outside.md', node=NODE)
        self.assertEqual(outside.read_text(encoding='utf-8'), 'keep')
        (self.skill / 'scripts/apply-feedback.mjs').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            adapter.start(self.project, 'second', 'test', self.skill, NODE)
        self.assertFalse((self.root / 'second').exists())

    def test_upstream_that_ignores_dry_run_is_refused_before_using_user_feedback(self):
        self.start(); self.write_feedback(); before = self.spec.read_bytes()
        source = self.skill / 'scripts/apply-feedback.mjs'
        source.write_text(APPLY.replace("if(process.argv.includes('--dry-run')) process.exit(0);", ''), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'dry-run changed'):
            adapter.invoke(self.project, 'trial', self.skill, 'apply', feedback='feedback-v1.md', node=NODE, dry_run=True)
        self.assertEqual(self.spec.read_bytes(), before)
        self.assertFalse((self.directory / 'spec-v1.json').exists())

    def test_external_command_has_lease_and_preserves_exit_code(self):
        self.start()
        code = "import json,os,pathlib; p=pathlib.Path(os.environ['SMYW_ARTIFACT_DIR']); assert json.loads((p.parents[1]/'run.json').read_text())['consumers']; raise SystemExit(7)"
        self.assertEqual(adapter.execute(self.project, 'trial', [sys.executable, '-c', code]), 7)
        self.assertEqual(life.load(self.root, 'trial')[2]['consumers'], [])


if __name__ == '__main__':
    unittest.main()
