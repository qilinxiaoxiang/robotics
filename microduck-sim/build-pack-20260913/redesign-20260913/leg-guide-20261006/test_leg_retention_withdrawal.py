"""Exercise the real adapter into a temporary output directory, never the active guide."""
import copy,importlib.util,json,pathlib,tempfile,unittest
G=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('leg_adapter',G/'build_leg_wiring_adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Withdrawal(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();out=pathlib.Path(cls.temp.name)
  (out/'full-build-data.json').write_bytes((G/'full-build-data.json').read_bytes())
  oldG=a.G;a.G=out
  try:a.main()
  finally:a.G=oldG
  cls.w=json.loads((out/'wiring-guide-data.json').read_text());cls.s=json.loads((out/'wiring-spatial-data.json').read_text())
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_six_artificial_frames_withdrawn_not_relabelled(self):
  self.assertEqual(self.s['checkedLegRetentionMeshes'],[])
  withdrawal=self.w['withdrawnLegRetentionDesign'];self.assertEqual(withdrawal['status'],'withdrawn');self.assertEqual(len(set(withdrawal['keys'])),6);self.assertFalse(withdrawal['replacementRetentionDesignAccepted']);self.assertEqual(withdrawal['replacementPrintedParts'],[])
  for c in self.s['connections']:
   if c.get('checkedLegRoute'):self.assertEqual(c['checkedLegRoute']['retentionMeshKeys'],[])
 def test_connector_only_view_retains_real_plugs(self):
  m=a.read(a.M);actual={p['key']:p for p in self.s['checkedLegMeshes']};self.assertEqual(len(actual),16)
  ports={r[k] for r in m['routes'] for k in ['fromPort','toPort']}
  for p in m['parts']:
   if p['key'] in ports:self.assertEqual(actual[p['key']],a.packed_mesh(p))
  for c in self.s['connections']:
   r=c.get('checkedLegRoute')
   if r:
    self.assertEqual(r['representation'],'connector-and-channel');self.assertFalse(r['softCableShapeSpecified']);self.assertEqual(set(r['meshKeys']),set(r['portIds']));self.assertTrue(r['channelInstruction'])
 def test_no_soft_wire_or_keeper_solids_are_shipped(self):
  self.assertFalse(any(p['kind'] in ['wire','bundle-illustration'] for p in self.s['checkedLegMeshes']))
 def test_original_topology_and_preplug_deadlines_preserved(self):
  expected={'right-leg':['ttl-05-04','ttl-04-03','ttl-03-02','ttl-02-01'],'left-leg':['ttl-10-09','ttl-09-08','ttl-08-07','ttl-07-06']}
  for k,v in expected.items():self.assertEqual(next(g['connectionIds']for g in self.w['groups']if g['id']==k),v)
  self.assertFalse(any(c['id']=='ttl-01-06' for c in self.w['connections']))
  for op in ['left-leg-01','right-leg-01','left-leg-05','right-leg-05','right-leg-13']:
   self.assertTrue(self.w['assemblyCablePrerequisites'].get(op),op)
  for c in self.w['connections']:
   if not c.get('checkedLegRoute'):continue
   prose=json.dumps(c['tutorial']).lower();self.assertNotIn('keeper',prose);self.assertNotIn('adjustable case tie',prose)
   self.assertTrue(c['assemblyOrder']['connectorBeforeClosure'])
   for phase in ['prepare','assemble','check']:self.assertTrue(c['tutorial'][phase])
if __name__=='__main__':unittest.main()
