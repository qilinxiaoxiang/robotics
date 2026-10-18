import copy
import unittest
from unittest.mock import patch
import tempfile
import json
from pathlib import Path
import build_body_wiring_adapter as body
import build_imu_wiring_adapter as imu

class IMUAdapter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  raw=[body.read(body.G/n) for n in ['full-build-data.json','wiring-guide-data.json','wiring-spatial-data.json']]
  import bundle_guide
  revision=body.G.parent/'fastener-review-20261008/fastener-patch-proposal.json'
  raw[0]=bundle_guide.apply_fastener_revision(raw[0],body.read(revision),revision)
  cls.inputs=body.apply_body_wiring_adapter(*raw)
  cls.before=copy.deepcopy(cls.inputs)
  cls.outputs=imu.apply_imu_wiring_adapter(*cls.inputs)

 def test_only_expected_parts_changed_and_world_transform_once(self):
  self.assertEqual(self.inputs,self.before)
  before={p['key']:p for p in self.inputs[0]['parts']};after={p['key']:p for p in self.outputs[0]['parts']}
  self.assertEqual(set(after)-set(before),{'imu_sh4_receiving'})
  for key in before:
   if key not in ['imu_clamp','imu_board','imu_cover']:self.assertEqual(before[key],after[key])
  p=after['imu_board'];self.assertEqual(p['sourceTransformWorld'],imu.IDENTITY)
  self.assertEqual(p['manufacturerSourceToWorld'],[[0,0,-1,-53],[1,0,0,-12.7],[0,-1,0,26.43],[0,0,0,1]])
  self.assertEqual(p['bounds'],next(p['expectedFinalBoundsMm'] for p in body.read(imu.DEFAULT_MANIFEST)['parts'] if p['key']=='imu_board'))

 def test_real_sequence_and_only_checked_moves(self):
  module=next(m for m in self.outputs[0]['modules'] if m['id']=='imu');ops=module['operations']
  self.assertEqual([p['id'] for p in ops],['imu-local-'+x for x in ['holder','board','plug','cover','fasten','retain']])
  self.assertEqual(ops[0]['partApproachVectors'],{'imu_clamp':[-28,0,0]})
  self.assertEqual(ops[1]['partApproachVectors'],{'imu_board':[-25,0,0]})
  self.assertEqual(ops[2]['partApproachVectors'],{'imu_sh4_receiving':[0,-12,0]})
  self.assertEqual(ops[3]['partApproachVectors'],{'imu_cover':[-20,0,0]})
  self.assertEqual(len(ops[4]['screwIds']),4)
  self.assertNotIn('partApproachVectors',ops[5]);self.assertNotIn('imu_cover',ops[2]['visiblePartKeys'])
  self.assertTrue(all(op['tutorial'][k] for op in ops for k in ['prepare','assemble','check']))

 def test_body_and_all_leg_receipts_unchanged(self):
  for old,new in zip(self.inputs[1:],self.outputs[1:]):
   unaffected={c['id']:c for c in old['connections'] if c['id'] not in {x[2] for x in imu.NETS}}
   self.assertEqual(unaffected,{c['id']:c for c in new['connections'] if c['id'] in unaffected})
  for key in ['checkedLegMeshes','checkedLegRetentionMeshes','bodyWiringAdapter']:
   self.assertEqual(self.inputs[2][key],self.outputs[2][key])
  self.assertEqual(self.outputs[2]['checkedHarnessMeshes'][:22],self.inputs[2]['checkedHarnessMeshes'])

 def test_free_ends_not_misrepresented_as_pi(self):
  d,w,s=self.outputs;keys={p['key'] for p in s['checkedHarnessMeshes']}
  self.assertEqual(len(keys),30)
  for _,label,cid,pin in imu.NETS:
   c=next(c for c in w['connections'] if c['id']==cid)
   self.assertIn('Open neck-root',c['to']);self.assertEqual(c['nominalCableLengthMm'],150)
   self.assertLess(c['lengthBoundary']['remainingNominalMm'],24)
   r=next(c['checkedHarnessRoute'] for c in s['connections'] if c['id']==cid)
   self.assertTrue(set(r['meshKeys']+r['contextMeshKeys'])<=keys)
   self.assertTrue(next(e for e in r['endpoints'] if e['role']=='to')['illustrativeOnly'])
   self.assertFalse(r['wholeHarnessAccepted'])

 def test_stale_manifest_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'m.json';m=body.read(imu.DEFAULT_MANIFEST);m['parts'][2]['sourceToWorld'][0][0]=-1;p.write_text(json.dumps(m))
   with self.assertRaises(ValueError):imu.load_verified_manifest(p)

 def test_failed_local_receipt_rejected_under_valid_release_pin(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);m=body.read(imu.DEFAULT_MANIFEST);r=body.read(m['acceptance']['report']);r['passed']=False
   rf=t/'receipt.json';rf.write_text(json.dumps(r));m['acceptance']['report']=str(rf);m['acceptance']['sha256']=body.sha(rf)
   mf=t/'manifest.json';mf.write_text(json.dumps(m))
   with patch.object(imu,'ACCEPTED_MANIFEST_SHA256',body.sha(mf)):
    with self.assertRaisesRegex(ValueError,'local check failed'):imu.load_verified_manifest(mf)

if __name__=='__main__':unittest.main()
