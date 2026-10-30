import importlib.util
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

SOURCE = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts/artifact_lifecycle.py'
spec = importlib.util.spec_from_file_location('lifecycle', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'owned'
        m.enroll(self.root)
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def at(self, days): return (self.now + timedelta(days=days)).isoformat()
    def add(self, name='one', kind='evidence'):
        p = Path(m.register(self.root,name,'test','synthetic only',kind))
        (p/'x.txt').write_text('fixture',encoding='utf-8')
        return p
    def status(self, day, apply=False): return m.sweep(self.root,apply,self.at(day))[0]['status']
    def test_exact_30_day_boundary(self):
        p=self.add(); m.close(self.root,'one',now=self.at(0))
        self.assertEqual(self.status(29.99,True),'retained')
        self.assertEqual(self.status(30),'due'); self.assertTrue((p/'x.txt').exists())
        self.assertEqual(self.status(30,True),'deleted'); self.assertFalse((p/'x.txt').exists())
    def test_60_days(self):
        self.add(); m.close(self.root,'one',60,self.at(0))
        self.assertEqual(self.status(30,True),'retained'); self.assertEqual(self.status(60,True),'deleted')
    def test_permanent(self):
        p=self.add(kind='permanent'); m.close(self.root,'one',now=self.at(0))
        self.assertEqual(self.status(1000,True),'permanent'); self.assertTrue((p/'x.txt').exists())
    def test_active_crash_is_not_closure(self):
        self.add(); self.assertEqual(self.status(1000,True),'active')
    def test_hold_review_does_not_delete(self):
        self.add(); m.close(self.root,'one',now=self.at(0)); m.hold(self.root,'one','pending','readback',self.at(1))
        self.assertEqual(self.status(31,True),'review-due')
    def test_release_grace(self):
        self.add(); m.close(self.root,'one',now=self.at(0)); m.hold(self.root,'one','pending','done',self.at(1))
        m.release(self.root,'one',self.at(40))
        self.assertEqual(self.status(46,True),'retained'); self.assertEqual(self.status(47,True),'deleted')
    def test_release_active_does_not_start_clock(self):
        self.add(); m.hold(self.root,'one','pending','done',self.at(0)); m.release(self.root,'one',self.at(40))
        self.assertEqual(self.status(100),'active'); m.close(self.root,'one',now=self.at(100))
        self.assertEqual(self.status(129),'retained')
    def test_changed_or_added_content_protected(self):
        p=self.add(); m.close(self.root,'one',now=self.at(0)); (p/'x.txt').write_text('new',encoding='utf-8')
        self.assertEqual(self.status(90,True),'changed')
    def test_unknown_existing_root_not_enrolled(self):
        with self.assertRaises(ValueError): m.enroll(self.root)
    def test_escape_rejected(self):
        with self.assertRaises(ValueError): m.register(self.root,'../outside','test','test')
    def test_work_immediate_after_explicit_close(self):
        self.add(kind='work'); m.close(self.root,'one',now=self.at(0)); self.assertEqual(self.status(0,True),'deleted')
    def test_record_expiration(self):
        self.add(); m.close(self.root,'one',now=self.at(0)); self.status(30,True)
        self.assertEqual(self.status(60,True),'receipt-expired')
    def test_custom_deadline(self):
        self.add(); m.close(self.root,'one',now=self.at(0),deadline=self.at(90))
        self.assertEqual(self.status(60),'retained'); self.assertEqual(self.status(90),'due')
    def test_lease_blocks_sweep(self):
        import subprocess,sys
        with m.lock(self.root):
            p=subprocess.run([sys.executable,str(SOURCE),'sweep','--root',str(self.root)],capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(p.returncode,0)
    def test_partial_failure_retry(self):
        from unittest.mock import patch
        self.add(); m.close(self.root,'one',now=self.at(0))
        original=Path.unlink
        def fail(path,*args,**kwargs):
            if path.name=='x.txt': raise PermissionError('synthetic failure')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',fail): self.assertEqual(self.status(30,True),'error')
        self.assertEqual(self.status(31,True),'deleted')

    def test_notifications_deduplicate_and_reset(self):
        rows=[{'id':'one','status':'review-due'}]
        self.assertEqual(m.notices(self.root,rows),rows)
        self.assertEqual(m.notices(self.root,rows),[])
        self.assertEqual(m.notices(self.root,[]),[])
        self.assertEqual(m.notices(self.root,rows),rows)
    def test_independent_groups(self):
        self.add('one'); self.add('two')
        m.close(self.root,'one',now=self.at(0))
        rows=m.sweep(self.root,True,self.at(30))
        self.assertEqual({v['id']:v['status'] for v in rows},{'one':'deleted','two':'active'})
    def test_damaged_record_is_preserved(self):
        p=self.add(); record=p.parent/'record.json'
        record.write_text('{}',encoding='utf-8')
        self.assertEqual(self.status(100,True),'error')
        self.assertTrue((p/'x.txt').exists())
    def test_symlink_is_refused(self):
        p=self.add(); target=Path(self.temp.name)/'original'
        target.write_text('protected',encoding='utf-8')
        try: (p/'link').symlink_to(target)
        except OSError as exc: self.skipTest('host symlink privilege unavailable: '+str(exc))
        with self.assertRaises(ValueError): m.close(self.root,'one',now=self.at(0))
        self.assertEqual(target.read_text(encoding='utf-8'),'protected')
    def test_check_does_not_mutate_records(self):
        self.add(); m.close(self.root,'one',now=self.at(0))
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.status(30)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
