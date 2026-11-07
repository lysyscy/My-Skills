import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
import impeccable_artifacts as adapter
life = adapter.life

class ImpeccableArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.root = self.project / '.artifacts/runs'
        life.enroll(self.root,project=self.project)

    def start(self, paths=None):
        return adapter.start(self.project,'trial','test',paths or ['.impeccable/mocks/trial'])

    def write(self,name,text='synthetic'):
        p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');return p

    def test_collect_and_expire_only_declared_outputs(self):
        permanent=self.write('DESIGN.md','keep')
        unrelated=self.write('.impeccable/mocks/other/picture.txt','other')
        self.start()
        own=self.write('.impeccable/mocks/trial/picture.txt')
        adapter.finish(self.project,'trial',confirmed=True)
        self.assertFalse(own.exists())
        archived=self.root/'trial/evidence/.impeccable/mocks/trial/picture.txt'
        self.assertEqual(archived.read_text(),'synthetic')
        state=life.load(self.root,'trial')[2]
        self.assertEqual(life.stamp(state['expires_at'])-life.stamp(state['closed_at']),timedelta(days=30))
        life.sweep(self.root,True,state['expires_at'])
        self.assertFalse(archived.exists());self.assertEqual(permanent.read_text(),'keep');self.assertEqual(unrelated.read_text(),'other')

    def test_generic_close_cannot_leave_native_outputs_unmanaged(self):
        self.start()
        source=self.write('.impeccable/mocks/trial/output.txt')
        with self.assertRaisesRegex(ValueError,'collection'):
            life.close(self.root,'trial')
        self.assertTrue(source.exists())
        adapter.finish(self.project,'trial',confirmed=True)

    def test_retry_after_sealing_failure(self):
        self.start();self.write('.impeccable/mocks/trial/output.txt')
        with patch.object(life,'seal',side_effect=OSError('synthetic seal error')), self.assertRaises(OSError):
            adapter.finish(self.project,'trial',confirmed=True)
        adapter.finish(self.project,'trial',confirmed=True)
        self.assertEqual(life.load(self.root,'trial')[2]['state'],'closed')

    def test_existing_and_permanent_paths_are_never_adopted(self):
        original=self.write('.impeccable/prototypes/old/source.js')
        for path in ['.impeccable/prototypes/old','DESIGN.md','.impeccable/design.json','.impeccable/live/sessions','../escape','.impeccable/critique/ignore.md']:
            with self.subTest(path=path),self.assertRaises(ValueError):
                adapter.start(self.project,'refused','test',[path])
        self.assertEqual(original.read_text(),'synthetic')
        self.assertFalse((self.root/'refused').exists())

    def test_open_critique_and_persistent_ignore_are_protected(self):
        ignore=self.write('.impeccable/critique/ignore.md','permanent')
        marker=self.write('.impeccable/critique/.gitignore','*')
        self.start(['.impeccable/critique'])
        report=self.write('.impeccable/critique/trial.md','---\nclosed: false\n---\nreview')
        with self.assertRaisesRegex(ValueError,'unresolved'):
            adapter.finish(self.project,'trial',confirmed=True)
        report.write_text('---\nclosed: true\n---\nreview',encoding='utf-8')
        adapter.finish(self.project,'trial',confirmed=True)
        self.assertTrue(ignore.exists());self.assertTrue(marker.exists())

    def test_consumer_hold_and_confirmation_block_finish(self):
        self.start();self.write('.impeccable/mocks/trial/a.txt')
        with self.assertRaisesRegex(ValueError,'confirmation'):
            adapter.finish(self.project,'trial')
        with life.consume(self.root,'trial'):
            with self.assertRaisesRegex(ValueError,'consumer'):
                adapter.finish(self.project,'trial',confirmed=True)
        life.hold(self.root,'trial','still reviewing','owner finishes')
        with self.assertRaisesRegex(ValueError,'hold'):
            adapter.finish(self.project,'trial',confirmed=True)

    def test_concurrent_claim_is_refused(self):
        self.start()
        with self.assertRaisesRegex(ValueError,'active task'):
            adapter.start(self.project,'second','test',['.impeccable/mocks'])
        self.assertIsNotNone(life.load(self.root,'second')[2]['hold'])

    def test_partial_move_retries_without_overwriting_changed_output(self):
        self.start()
        self.write('.impeccable/mocks/trial/a.txt','a');self.write('.impeccable/mocks/trial/b.txt','b')
        original=os.replace
        def fail(source,target):
            if Path(source).name=='b.txt':raise PermissionError('occupied')
            return original(source,target)
        with patch.object(adapter.os,'replace',fail),self.assertRaises(PermissionError):
            adapter.finish(self.project,'trial',confirmed=True)
        self.assertEqual(life.load(self.root,'trial')[2]['state'],'active')
        self.write('.impeccable/mocks/trial/b.txt','changed')
        with self.assertRaisesRegex(ValueError,'changed'):
            adapter.finish(self.project,'trial',confirmed=True)
        self.write('.impeccable/mocks/trial/b.txt','b')
        adapter.finish(self.project,'trial',confirmed=True)
        self.assertEqual(life.load(self.root,'trial')[2]['state'],'closed')

    def test_link_is_refused_and_external_target_survives(self):
        self.start();outside=self.project/'external';outside.mkdir()
        source=self.project/'.impeccable/mocks/trial';source.mkdir(parents=True)
        if os.name=='nt':
            p=subprocess.run(['cmd','/c','mklink','/J',str(source/'linked'),str(outside)],capture_output=True)
            if p.returncode:self.skipTest('junction not available')
            self.addCleanup(lambda: os.rmdir(source/'linked'))
        else:
            (source/'linked').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'linked'):
            adapter.finish(self.project,'trial',confirmed=True)
        self.assertTrue(outside.exists())

    def test_real_command_keeps_consumer_and_preserves_exit_code(self):
        self.start()
        code="import json,os,pathlib; p=pathlib.Path(os.environ['IMPECCABLE_ARTIFACT_RUN']); assert json.loads((p/'run.json').read_text())['consumers']; raise SystemExit(7)"
        self.assertEqual(adapter.execute(self.project,'trial',[sys.executable,'-B','-c',code]),7)
        self.assertEqual(life.load(self.root,'trial')[2]['consumers'],[])
        self.assertEqual(life.load(self.root,'trial')[2]['state'],'active')

if __name__=='__main__':
    unittest.main()
