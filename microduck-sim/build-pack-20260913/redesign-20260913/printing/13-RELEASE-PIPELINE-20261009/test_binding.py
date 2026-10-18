"""Tamper an isolated copy of actual native fixture outputs; never touch inputs."""
from pathlib import Path
import tempfile,unittest,shutil,json,zipfile
import release_pipeline as r
from verify_release import verify
class BindingTests(unittest.TestCase):
 def test_real_native_fixture_chain(self):self.assertEqual(verify(r.HERE/'fixture-run')['files'],2)
 def test_actual_output_tamper_is_rejected(self):
  source=r.HERE/'fixture-run';idx=r.read(source/'delivery-index.json');target=Path(idx['files'][0]['path'])
  # Point a copied index to a deliberately changed private copy and rebind only
  # the outer index. Native/output/ZIP link must independently reject it.
  with tempfile.TemporaryDirectory()as td:
   d=Path(td);bad=d/target.name;bad.write_bytes(target.read_bytes()+b'TAMPER');idx['files'][0]['path']=str(bad);r.write(d/'delivery-index.json',idx);pkg=r.read(source/'package-receipt.json');pkg['index']=r.ref(d/'delivery-index.json');r.write(d/'package-receipt.json',pkg)
   with self.assertRaises(AssertionError):verify(d)
 def test_filename_time_tamper_is_rejected(self):
  source=r.HERE/'fixture-run';idx=r.read(source/'delivery-index.json');idx['files'][0]['estimatedSeconds']=1
  with tempfile.TemporaryDirectory()as td:
   d=Path(td);r.write(d/'delivery-index.json',idx);pkg=r.read(source/'package-receipt.json');pkg['index']=r.ref(d/'delivery-index.json');r.write(d/'package-receipt.json',pkg)
   with self.assertRaises(AssertionError):verify(d)
 def test_fixture_cannot_be_released(self):
  source=r.HERE/'fixture-run';idx=r.read(source/'delivery-index.json');idx['status']='RELEASED'
  with tempfile.TemporaryDirectory()as td:
   d=Path(td);r.write(d/'delivery-index.json',idx);pkg=r.read(source/'package-receipt.json');pkg['index']=r.ref(d/'delivery-index.json');r.write(d/'package-receipt.json',pkg)
   with self.assertRaises(AssertionError):verify(d)
if __name__=='__main__':unittest.main()
