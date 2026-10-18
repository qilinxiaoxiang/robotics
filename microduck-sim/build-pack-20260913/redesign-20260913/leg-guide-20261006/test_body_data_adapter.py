import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_body_wiring_adapter as b
import build_body_data_adapter as a

class BodyData(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.inputs=b.apply_body_wiring_adapter(*[b.read(b.G/n) for n in ['full-build-data.json','wiring-guide-data.json','wiring-spatial-data.json']])
  cls.before=copy.deepcopy(cls.inputs);cls.outputs=a.apply_body_data_adapter(*cls.inputs)

 def test_immutable_inputs_and_eight_legs_five_power_ids(self):
  self.assertEqual(self.inputs,self.before)
  for old,new in zip(self.inputs[1:],self.outputs[1:]):
   self.assertEqual([c for c in old['connections'] if c['id'] in b.LEG_IDS],[c for c in new['connections'] if c['id'] in b.LEG_IDS])
  for key in ['checkedLegMeshes','checkedLegRetentionMeshes']:self.assertEqual(self.inputs[2][key],self.outputs[2][key])
  for cid in b.TITLES:
   self.assertEqual(next(c for c in self.inputs[1]['connections'] if c['id']==cid),next(c for c in self.outputs[1]['connections'] if c['id']==cid))
  self.assertEqual(self.inputs[0]['parts'],self.outputs[0]['parts'])

 def test_all_navigation_ids_exist_and_old_data_curve_removed(self):
  _,w,s=self.outputs;ids={c['id'] for c in w['connections']};stepids={c['id'] for step in w['steps'] for c in step['connections']}
  self.assertNotIn('data-06',ids);self.assertNotIn('data-06',{c['id'] for c in s['connections']})
  self.assertTrue(a.DATA_IDS|a.HOUSING_IDS<=ids)
  for group in w['groups']:self.assertTrue(set(group['connectionIds'])<=stepids)
  for c in w['connections']:
   if c['id'] in a.DATA_IDS|a.HOUSING_IDS:
    self.assertTrue(all(c['tutorial'][p] for p in ['prepare','assemble','check']))
    self.assertIn(c['moduleId'],{g['id'] for g in w['groups']})

 def test_real_closure_dependencies(self):
  p=self.outputs[1]['assemblyCablePrerequisites']
  required=set().union(*(set(x['connectionIds']) for x in p['neck-13']))
  self.assertTrue(a.DATA_IDS|a.HOUSING_IDS<=required)
  self.assertTrue(any('ttl-12-05-data-only' in x['connectionIds'] for x in p['neck-01']))
  self.assertTrue(any('zone-10-three-contact-termination' in x['connectionIds'] for x in p['body-power-04']))

 def test_only_housing_moves_on_bench_no_whole_flexible_translation(self):
  s=self.outputs[2];keys={p['key'] for p in s['checkedHarnessMeshes']}
  self.assertEqual(len(keys),26)
  for c in s['connections']:
   if c['id'] not in a.DATA_IDS|a.HOUSING_IDS:continue
   r=c['checkedHarnessRoute'];self.assertTrue(set(r['meshKeys']+r['contextMeshKeys'])<=keys);self.assertFalse(c['segments'])
   if c['id'] in a.HOUSING_IDS:
    bench=r['benchInsertion'][0]
    self.assertEqual(len(bench['movingMeshKeys']),1);self.assertIn('housing',bench['movingMeshKeys'][0])
    self.assertEqual(bench['approachMm'],12);self.assertEqual(bench['seatedOffsetMm'],[0,0,0])
    self.assertTrue(bench['openAssemblyOnly']);self.assertFalse(bench['ownMatingMaterialVerified'])
    self.assertTrue(set(bench['fixedMeshKeys'])<=keys)
   else:self.assertNotIn('benchInsertion',r)
  free=next(c for c in s['connections'] if c['id']=='ttl-openrb-10-data-body')['checkedHarnessRoute']['endpoints'][0]
  self.assertTrue(free['illustrativeOnly']);self.assertEqual(free['position'],[6,1,55])

 def test_mutated_animation_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   m=b.read(a.HOUSING_MANIFEST);m['connections'][0]['matingAnimation']['approachVectorMm']=[12,0,0]
   p=Path(td)/'m.json';p.write_text(json.dumps(m))
   with self.assertRaises(ValueError):a.load_verified_manifest(p,a.PINS[str(a.HOUSING_MANIFEST)])

 def test_failed_receipt_rejected_even_with_ready_flag(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);m=b.read(a.DATA_MANIFEST);r=b.read(m['receipt']);r['passed']=False
   rp=td/'r.json';rp.write_text(json.dumps(r));m['receipt']=str(rp);m['receiptSha256']=b.sha(rp)
   mp=td/'m.json';mp.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'receipt failed'):a.load_verified_manifest(mp,b.sha(mp))

 def test_missing_actual_shell_deadline_rejected(self):
  d,w,s=copy.deepcopy(self.inputs)
  for mod in d['modules']:
   for op in mod['operations']:
    op['add']=[x for x in op['add'] if x not in ['shell_left','shell_right']]
  with self.assertRaisesRegex(ValueError,'closure dependency missing'):a.apply_body_data_adapter(d,w,s)

if __name__=='__main__':unittest.main()
