"""Standard-library-only tests of receipt coverage; no CAD imports/execution."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import compact_neutral_worker as w
class Coverage(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.patch=patch.object(w,'OUT',self.d);self.patch.start();(self.d/'pairs').mkdir();self.center={'points':[]};w.save(self.d/'centerline.json',self.center);w.save(self.d/'plan.json',{});(self.d/'receiving-world.stl').write_bytes(b'fixture only - not actual mesh')
  w.save(self.d/'self-check.json',{'passed':True,'centerlineSha256':w.sha(self.d/'centerline.json')});w.save(self.d/'mesh.json',{'meshSha256':w.sha(self.d/'receiving-world.stl'),'centerlineSha256':w.sha(self.d/'centerline.json'),'selfCheckSha256':w.sha(self.d/'self-check.json')})
  self.p={'expectedPairs':[{'pose':'neutral','obstacle':k} for k in ['a','b']],'obstacles':[{'key':k,'sha256':'source-'+k} for k in ['a','b']]}
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def receipt(self,k,passed=True,plan=None):w.save(self.d/'pairs'/(k+'.json'),{'key':k,'planSha256':plan or w.sha(self.d/'plan.json'),'meshSha256':w.sha(self.d/'receiving-world.stl'),'obstacleSha256':'source-'+k,'passed':passed})
 def run_summary(self):
  with patch.object(w,'require_guard',lambda:None),patch.object(w,'required_centerline',lambda:(self.p,self.center)),contextlib.redirect_stdout(io.StringIO()):w.summary()
  return json.loads((self.d/'summary.json').read_text())
 def test_missing_is_incomplete(self):
  self.receipt('a');r=self.run_summary();self.assertFalse(r['coverageComplete']);self.assertFalse(r['neutralClear']);self.assertEqual(r['missingPairs'],['b'])
 def test_stale_is_incomplete(self):
  self.receipt('a');self.receipt('b',plan='old');r=self.run_summary();self.assertFalse(r['coverageComplete']);self.assertEqual(r['stalePairs'],['b'])
 def test_failed_is_not_clear(self):
  self.receipt('a');self.receipt('b',False);r=self.run_summary();self.assertTrue(r['coverageComplete']);self.assertFalse(r['neutralClear'])
 def test_all_pairs_cannot_close_whole_harness(self):
  self.receipt('a');self.receipt('b');r=self.run_summary();self.assertTrue(r['neutralClear']);self.assertFalse(r['wholeHarnessAccepted'])
 def test_stale_mesh_is_incomplete(self):
  self.receipt('a');self.receipt('b');(self.d/'receiving-world.stl').write_bytes(b'changed');r=self.run_summary();self.assertFalse(r['meshCurrent']);self.assertFalse(r['neutralClear'])
 def test_self_failure_blocks_summary(self):
  self.receipt('a');self.receipt('b');w.save(self.d/'self-check.json',{'passed':False,'centerlineSha256':w.sha(self.d/'centerline.json')});r=self.run_summary();self.assertFalse(r['selfCheckPassed']);self.assertFalse(r['neutralClear'])
if __name__=='__main__':unittest.main()
