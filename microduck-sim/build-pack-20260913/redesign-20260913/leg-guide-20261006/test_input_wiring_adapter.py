import copy,json,tempfile,unittest
from pathlib import Path
import build_body_wiring_adapter as b
import build_body_data_adapter as bd
import build_imu_wiring_adapter as imu
import build_input_wiring_adapter as a

class InputAdapter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import bundle_guide
  raw=[b.read(b.G/n) for n in ['full-build-data.json','wiring-guide-data.json','wiring-spatial-data.json']]
  revision=b.G.parent/'fastener-review-20261008/fastener-patch-proposal.json'
  raw[0]=bundle_guide.apply_fastener_revision(raw[0],b.read(revision),revision)
  cls.inputs=bd.apply_body_data_adapter(*imu.apply_imu_wiring_adapter(*b.apply_body_wiring_adapter(*raw)))
  cls.before=copy.deepcopy(cls.inputs);cls.outputs=a.apply_input_wiring_adapter(*cls.inputs)

 def test_preserves_all_prior_routes_parts_meshes_and_inputs(self):
  self.assertEqual(self.inputs,self.before)
  self.assertEqual(self.inputs[0]['parts'],self.outputs[0]['parts'])
  for old,new in zip(self.inputs[1:],self.outputs[1:]):
   ids={x['id']:x for x in old['connections'] if x['id'] not in a.RETIRED}
   self.assertEqual(ids,{x['id']:x for x in new['connections'] if x['id'] in ids})
  for k in ['checkedLegMeshes','checkedLegRetentionMeshes']:self.assertEqual(self.inputs[2][k],self.outputs[2][k])
  self.assertEqual(self.inputs[2]['checkedHarnessMeshes'],self.outputs[2]['checkedHarnessMeshes'][:-4])
  ids={c['id'] for c in self.outputs[1]['connections']}
  self.assertTrue(b.LEG_IDS|set(b.TITLES)|bd.DATA_IDS|bd.HOUSING_IDS|{'imu-gnd','imu-vin','imu-sda','imu-scl'}<=ids)

 def test_exact_local_meshes_no_fake_external_connector_or_motion(self):
  _,w,s=self.outputs;route=next(c for c in s['connections'] if c['id']==a.CID)
  r=route['checkedHarnessRoute'];self.assertEqual(route['segments'],[])
  self.assertEqual(set(r['meshKeys']),a.KEYS);self.assertEqual(len(r['endpoints']),4)
  self.assertEqual([e['position'] for e in r['endpoints'][:2]],[[-42.2,7.5,-45],[-42.2,-3.8,-45]])
  self.assertEqual(r['endpoints'][2]['position'],[-31.5,10.9,0]);self.assertEqual(r['endpoints'][3]['position'],[-33.5,-3.8,17])
  self.assertNotIn('benchInsertion',r);self.assertNotIn('matingAnimation',r)
  self.assertFalse(r['wholeHarnessAccepted']);self.assertFalse(r['partKeys'])
  keys={p['key'] for p in s['checkedHarnessMeshes']};self.assertTrue(set(r['contextMeshKeys']+r['coverMeshKeys'])<=keys)
  for obj in [w,s]:self.assertFalse(a.RETIRED&{c['id'] for c in obj['connections']})

 def test_stage_navigation_and_preclosure_order(self):
  d,w,s=self.outputs;ids={c['id'] for c in w['connections']};stepids={c['id'] for x in w['steps'] for c in x['connections']}
  for g in w['groups']:self.assertTrue(set(g['connectionIds'])<=stepids)
  for x in w['steps']:self.assertTrue(set(x['connectionIds'])<=ids)
  self.assertEqual(next(g for g in w['groups'] if g['id']=='torso-power')['connectionIds'][0],a.CID)
  ops=[o for m in d['modules'] for o in m['operations']];ix={o['id']:i for i,o in enumerate(ops)}
  self.assertLess(ix['body-power-01'],ix['body-power-02']);self.assertLess(ix['body-power-02'],ix['body-power-03']);self.assertLess(ix['body-power-03'],ix['neck-13'])
  for oid in ['body-power-01','body-power-03','body-power-06','neck-13']:
   self.assertTrue(any(a.CID in p['connectionIds'] for p in w['assemblyCablePrerequisites'][oid]))
  text=next(o for o in ops if o['id']=='body-power-01')['text'];self.assertIn('unterminated',text);self.assertNotIn('Connect the 2 m',text)

 def test_user_copy_explains_actions_without_geometry_implementation_terms(self):
  c=next(c for c in self.outputs[1]['connections'] if c['id']==a.CID)
  display=' '.join(c['notes']+[c['wire']]+sum(c['tutorial'].values(),[]))
  for term in ['receiving','source-bound','STL','boundary','[-33','registered']:self.assertNotIn(term,display)
  self.assertIn('two-metre',display);self.assertIn('5.6 mm',display)
  self.assertEqual(c['sourceTutorial'],b.read(a.MANIFEST)['connections'][0]['tutorial'])

 def test_failed_receipt_cannot_be_bypassed_by_ready(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);m=b.read(a.MANIFEST);r=b.read(m['receipt']);r['selfClear']=False
   rp=td/'r.json';rp.write_text(json.dumps(r));m['receipt']=str(rp);m['receiptSha256']=b.sha(rp)
   mp=td/'m.json';mp.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'receipt failed'):a.load_verified_manifest(mp,b.sha(mp))

 def test_modified_source_rejected_despite_rehashed_manifest(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);m=b.read(a.MANIFEST);p=td/'bad.stl';p.write_bytes(b'changed geometry');m['additionalParts'][0]['file']=str(p)
   mp=td/'m.json';mp.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'stale source'):a.load_verified_manifest(mp,b.sha(mp))

 def test_missing_closure_or_upstream_adapter_rejected(self):
  d,w,s=copy.deepcopy(self.inputs)
  for mod in d['modules']:
   for op in mod['operations']:op['add']=[x for x in op.get('add',[]) if x not in ['shell_left','shell_right']]
  with self.assertRaisesRegex(ValueError,'closure deadline missing'):a.apply_input_wiring_adapter(d,w,s)
  d,w,s=copy.deepcopy(self.inputs);w.pop('bodyDataAdapter')
  with self.assertRaisesRegex(ValueError,'DATA and IMU'):a.apply_input_wiring_adapter(d,w,s)

if __name__=='__main__':unittest.main()
