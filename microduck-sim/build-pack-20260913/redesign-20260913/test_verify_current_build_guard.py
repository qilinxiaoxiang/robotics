"""Exercise CLI dispatch without running a generator or writing an acceptance artifact."""
from pathlib import Path
import contextlib,copy,io,json,runpy,sys,unittest
from types import SimpleNamespace
from unittest.mock import patch

P=Path(__file__).resolve().parent
SCRIPT=P/'verify_current_build.py'
CONTEXT=P.parent.parent/'PROJECT-CONTEXT.json'
REAL_CONTEXT=json.loads(CONTEXT.read_text())

class CurrentBuildGuard(unittest.TestCase):
 def invoke(self,args,context=None):
  calls=[];writes=[];stdout=io.StringIO();stderr=io.StringIO();original_read=Path.read_text
  def read(path,*aa,**kw):
   if path==CONTEXT:return json.dumps(context if context is not None else REAL_CONTEXT)
   return original_read(path,*aa,**kw)
  def run(cmd,**kw):calls.append(list(cmd));return SimpleNamespace(returncode=0,stdout='',stderr='')
  def write(path,text,*aa,**kw):writes.append((str(path),json.loads(text)));return len(text)
  with patch.object(sys,'argv',[str(SCRIPT),*args]),patch.object(Path,'read_text',read),patch.object(Path,'write_text',write),patch('subprocess.run',run),patch('subprocess.call',lambda cmd:(calls.append(list(cmd)),0)[1]),contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
   try:runpy.run_path(str(SCRIPT),run_name='__main__')
   except SystemExit as exc:status=exc.code
   else:status=0
  return status,calls,writes,stdout.getvalue()

 def test_all_existing_argument_combinations_fail_closed(self):
  for scope in ['design','project']:
   for historical in [[],['--historical-baseline']]:
    for cad in [[],['--cad-python','/untrusted/old-cad']]:
     with self.subTest(scope=scope,historical=historical,cad=cad):
      status,calls,writes,out=self.invoke(['--scope',scope,*historical,*cad])
      self.assertEqual(status,1);self.assertEqual(calls,[])
      self.assertEqual([p for p,_ in writes],[str(P/'current-build-verification.json')])
      report=writes[0][1];self.assertFalse(report['passed']);self.assertFalse(report['historicalGeneratorsExecuted'])
      self.assertEqual(report['scope'],scope);self.assertEqual(report['physical_tests'],0)
      self.assertEqual(report['historicalBaselineRequested'],bool(historical))

 def test_empty_active_repair_cannot_fall_back_to_legacy(self):
  context=copy.deepcopy(REAL_CONTEXT);context['current_build']['staged_review_20261009']['activeRepair']={}
  status,calls,writes,_=self.invoke(['--historical-baseline'],context)
  self.assertEqual(status,1);self.assertEqual(calls,[]);self.assertFalse(writes[0][1]['passed'])

 def test_historical_flag_without_active_repair_is_read_only(self):
  context=copy.deepcopy(REAL_CONTEXT);context['current_build']['staged_review_20261009'].pop('activeRepair')
  status,calls,writes,out=self.invoke(['--historical-baseline'],context)
  self.assertEqual(status,1);self.assertEqual(calls,[]);self.assertEqual(writes,[])
  self.assertTrue(json.loads(out)['historicalBaselineOnly']);self.assertFalse(json.loads(out)['passed'])

 def test_help_and_bad_scope_never_call_generators(self):
  for args,code in [(['--help'],0),(['--scope','invented'],2)]:
   status,calls,writes,_=self.invoke(args);self.assertEqual(status,code);self.assertEqual(calls,[]);self.assertEqual(writes,[])

 def test_only_explicit_active_verifier_can_be_dispatched(self):
  context=copy.deepcopy(REAL_CONTEXT);active=context['current_build']['staged_review_20261009']['activeRepair']
  # Existing read-only test file stands in for a future declared current verifier; subprocess is mocked.
  active['verifier']=str(Path(__file__).resolve().relative_to(P.parent.parent))
  status,calls,writes,_=self.invoke(['--scope','project','--historical-baseline'],context)
  self.assertEqual(status,0);self.assertEqual(calls,[[sys.executable,str(Path(__file__).resolve()),'--scope','project']]);self.assertEqual(writes,[])

if __name__=='__main__':unittest.main()
