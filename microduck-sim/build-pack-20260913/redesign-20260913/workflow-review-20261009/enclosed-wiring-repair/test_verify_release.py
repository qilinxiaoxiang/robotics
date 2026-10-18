"""Tiny synthetic files exercise acceptance boundaries; no CAD or generated guide."""
import json,tempfile,unittest,zipfile,subprocess,sys
from pathlib import Path
import verify_release as v

class ReleaseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name).resolve()
  self.context=self.p/'PROJECT-CONTEXT.json';self.write(self.context,{'required_capabilities':['camera_observation'],'current_build':{'contract':'contract.json'}})
  self.write(self.p/'contract.json',{'revision':'test-release'})
  self.m={'schemaVersion':1,'releaseRevision':'test-release','status':'ready','projectContext':self.ref(self.context),'artifacts':[],'gates':{}}
  for role in v.ROLE_GATE:
   if role in ['print_zip','printer_file']:continue
   p=self.p/(role+'.json');leaf=self.p/(role+'-geometry.stl');leaf.write_text('synthetic leaf')
   self.write(p,{'fixture':role,'sourceHashes':{leaf.name:v.sha(leaf)}});self.m['artifacts'].append(dict(self.ref(p),id=role,role=role))
  for machine in ['bambu','elegoo']:
   name='zhengxia_Black_'+machine+'.gcode';p=self.p/name;p.write_text('; tiny test fixture\n')
   self.m['artifacts'].append(dict(self.ref(p),id=machine,role='printer_file',machine=machine,color='Black',archiveEntry=name))
  zpath=self.p/'delivery.zip'
  with zipfile.ZipFile(zpath,'w') as z:
   for a in self.m['artifacts']:
    if a['role']=='printer_file':z.write(self.p/a['path'],a['archiveEntry'])
  self.m['artifacts'].append(dict(self.ref(zpath),id='zip',role='print_zip'));self.r={}
  for name,cov in v.COVERAGE.items():
   r={'passed':True,'complete':True,'unresolved':[],'releaseRevision':'test-release','coverage':sorted(cov),'sourceHashes':{a['path']:a['sha256'] for a in self.m['artifacts']}}
   if name=='head':r['wholeHeadAccepted']=True
   if name=='harness':r['wholeHarnessAccepted']=True
   if name=='liveDeployment':r.update(liveReadbackMatched=True,browserChecked=True,url='http://test.invalid/guide',checkedAt='test-fixture')
   self.r[name]=r;self.save_gate(name)
  self.path=self.p/'release-manifest.json';self.save()
 def write(self,p,x):p.write_text(json.dumps(x))
 def ref(self,p):return {'path':p.name,'sha256':v.sha(p)}
 def save(self):self.write(self.path,self.m)
 def save_gate(self,name):
  p=self.p/(name+'-receipt.json');self.write(p,self.r[name]);self.m['gates'][name]=self.ref(p)
 def review(self,scope='design',fn=None):
  self.save();return v.review(self.path,scope,self.context,fn)
 def codes(self,r):return {x['code'] for x in r['issues']}
 def snapshot(self):return {str(p.relative_to(self.p)):v.sha(p) for p in self.p.rglob('*') if p.is_file()}
 def test_valid_design_readonly_and_not_physical_acceptance(self):
  before=self.snapshot();r=v.review(self.path,'design',self.context)
  self.assertTrue(r['passed'],r);self.assertEqual(r['physicalTests'],0);self.assertEqual(before,self.snapshot())
 def test_required_head_cannot_be_replaced_by_body_local_receipt(self):
  self.r['head']['coverage']=['openrb'];self.r['head']['wholeHeadAccepted']=False;self.save_gate('head')
  r=self.review();self.assertFalse(r['passed']);self.assertIn('local_receipt_not_whole_acceptance',self.codes(r));self.assertIn('receipt_scope_incomplete',self.codes(r))
 def test_missing_categories_are_incomplete(self):
  for name in v.COVERAGE:
   old=self.m['gates'].pop(name);r=self.review();self.assertFalse(r['passed']);self.assertIn('missing_gate',self.codes(r));self.m['gates'][name]=old
 def test_changed_geometry_rejected(self):
  (self.p/'head_inventory.json').write_text('new geometry')
  self.assertIn('stale_artifact',self.codes(self.review()))
 def test_mutated_inventory_leaf_rejected(self):
  (self.p/'head_inventory-geometry.stl').write_text('changed leaf geometry')
  self.assertIn('stale_artifact',self.codes(self.review()))
 def test_missing_receipt_inventory_binding_rejected(self):
  self.r['guide']['sourceHashes'].pop('head_inventory.json');self.save_gate('guide')
  self.assertIn('receipt_does_not_bind_artifact',self.codes(self.review()))
 def test_zip_and_printer_file_bytes_must_match(self):
  with zipfile.ZipFile(self.p/'delivery.zip','w') as z:
   for machine in ['bambu','elegoo']:z.writestr('zhengxia_Black_'+machine+'.gcode','wrong bytes')
  self.m['artifacts'][-1]['sha256']=v.sha(self.p/'delivery.zip')
  self.r['print']['sourceHashes']['delivery.zip']=v.sha(self.p/'delivery.zip');self.save_gate('print')
  self.assertIn('print_archive_bytes_mismatch',self.codes(self.review()))
 def test_hash_only_deployment_is_not_browser_acceptance(self):
  self.r['liveDeployment']['browserChecked']=False;self.save_gate('liveDeployment')
  self.assertIn('live_deployment_incomplete',self.codes(self.review()))
 def test_project_keeps_canonical_visual_gate_even_when_design_passes(self):
  called=[]
  def fn(root):called.append(root);return {'training_evidence_verified':True,'physical_acceptance_verified':False,'project_handoff_ready':False}
  r=self.review('project',fn);self.assertTrue(r['designPassed']);self.assertFalse(r['passed']);self.assertIn('visual_pickup_not_accepted',self.codes(r));self.assertEqual(called,[self.p])
 def test_project_rejects_old_hardware_revision(self):
  r={'passed':True,'complete':True,'unresolved':[],'releaseRevision':'test-release','coverage':sorted(v.PROJECT_COVERAGE),'sourceHashes':{a['path']:a['sha256'] for a in self.m['artifacts']},'kind':'hardware_commissioning','physicalTests':1}
  p=self.p/'physical.json';self.write(p,r);self.m['projectAcceptance']=self.ref(p)
  self.write(self.p/'contract.json',{'revision':'old-build'})
  out=self.review('project',lambda root:{'training_evidence_verified':True,'physical_acceptance_verified':True,'project_handoff_ready':True})
  self.assertIn('project_build_revision_mismatch',self.codes(out))
 def test_cli_does_not_generate_on_missing_manifest_or_accept_legacy_escape(self):
  before=self.snapshot()
  result=subprocess.run([sys.executable,'-B',str(Path(v.__file__)),'--manifest',str(self.p/'absent.json')],capture_output=True,text=True)
  self.assertEqual(result.returncode,1);self.assertFalse(json.loads(result.stdout)['generatorsExecuted']);self.assertEqual(before,self.snapshot())
  result=subprocess.run([sys.executable,'-B',str(Path(v.__file__)),'--historical-baseline'],capture_output=True,text=True)
  self.assertEqual(result.returncode,2);self.assertEqual(before,self.snapshot())

if __name__=='__main__':unittest.main()
