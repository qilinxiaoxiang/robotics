"""Regression tests for the accepted body subset and rejected stale/failed sources."""
import base64
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import build_body_wiring_adapter as a

class BodyAdapter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.inputs=[a.read(a.G/n) for n in ['full-build-data.json','wiring-guide-data.json','wiring-spatial-data.json']]
  cls.snapshot=copy.deepcopy(cls.inputs)
  cls.outputs=a.apply_body_wiring_adapter(*cls.inputs)

 def test_pure_copy_and_all_eight_leg_routes_unchanged(self):
  self.assertEqual(self.inputs,self.snapshot)
  for before,after in zip(self.inputs[1:],self.outputs[1:]):
   self.assertEqual([c for c in before['connections'] if c['id'] in a.LEG_IDS],
                    [c for c in after['connections'] if c['id'] in a.LEG_IDS])
  for key in ['checkedLegMeshes','checkedLegRetentionMeshes','regionalLegAdapter']:
   self.assertEqual(self.inputs[2][key],self.outputs[2][key])
  old_steps={s['id']:s for s in self.inputs[1]['steps']}
  for step in self.outputs[1]['steps']:
   if step['id'] in old_steps:
    self.assertEqual([c for c in step['connections'] if c['id'] in a.LEG_IDS],
                     [c for c in old_steps[step['id']]['connections'] if c['id'] in a.LEG_IDS])

 def test_withdrawn_fuse_hardware_and_active_instructions_removed(self):
  d,w,s=self.outputs
  self.assertFalse(any('fuse_carrier' in p['key'] for p in d['parts']))
  self.assertFalse(any('fuse_carrier' in p['id'] for p in d['screws']))
  self.assertNotIn('M2 x 20 machine + M2 nut',d['screwTotals'])
  self.assertFalse(a.LEGACY_CONNECTIONS & {c['id'] for c in w['connections']})
  self.assertFalse(a.FUSE_NODES & {n['id'] for n in w['nodes']})
  active=[]
  for c in w['connections']:active.extend([c.get('from',''),c.get('to',''),c.get('wire',''),*c.get('notes',[])])
  for step in w['steps']:
   active.extend(step.get('actions',[]));active.append(step.get('check',''))
   self.assertEqual(step.get('connectionIds',[c['id'] for c in step['connections']]),[c['id'] for c in step['connections']])
  for text in active:
   self.assertNotRegex(text,r'F(?:0|9|10)\b|1→6|eleven fuse')

 def test_exact_native_context_not_duplicate_and_unconnected_head_boundary(self):
  d,w,s=self.outputs
  self.assertEqual(len(s['checkedHarnessMeshes']),22)
  keymap={p['key']:p for p in s['checkedHarnessMeshes']}
  for c in s['connections']:
   if 'checkedHarnessRoute' not in c:continue
   r=c['checkedHarnessRoute']; self.assertEqual(r['partKeys'],[])
   self.assertFalse(c['segments']); self.assertFalse(r['wholeHarnessAccepted'])
   self.assertEqual(set(r['coverMeshKeys']),{'body_context_shell_left','body_context_shell_right'})
   self.assertTrue(set(r['meshKeys']+r['contextMeshKeys'])<=keymap.keys())
  motor=keymap['body_context_motor10']
  self.assertEqual(motor['partKey'],'motor10');self.assertEqual(motor['importTranslationMm'],[0,-11,0])
  positions=struct.iter_unpack('<3f',base64.b64decode(motor['positionB64']))
  rows=list(positions); self.assertAlmostEqual(min(v[1] for v in rows),7.5,places=4)
  self.assertAlmostEqual(max(v[1] for v in rows),27.5,places=4)
  head=next(c['checkedHarnessRoute'] for c in s['connections'] if c['id']=='power-head-trunk')
  self.assertTrue(all(e['illustrativeOnly'] for e in head['endpoints'] if e['role']=='to'))

 def test_power_steps_are_inspection_not_fabricated_motion(self):
  d,w,_=self.outputs;power=next(m for m in d['modules'] if m['id']=='power')
  self.assertEqual(len(power['operations']),6)
  for op in power['operations']:
   self.assertTrue(op['id'].startswith('body-power-'));self.assertEqual(op['kind'],'inspect')
   self.assertEqual(op['add'],[]);self.assertEqual(op['screwIds'],[])
   self.assertNotIn('approachVector',op);self.assertNotIn('motionWaypoints',op)
   self.assertTrue(all(op['tutorial'][p] for p in ['prepare','assemble','check']))
  self.assertEqual(len(w['assemblyCablePrerequisites']['body-power-04'][0]['connectionIds']),2)

 def test_manifest_metadata_mutation_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=a.read(a.DEFAULT_MANIFEST);m['contextParts'][0]['importTranslationMm']=[999,0,0]
   file=Path(tmp)/'manifest.json';file.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'stale source'):a.load_verified_manifest(file)

 def _mutated_receipt(self, mutate):
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);m=a.read(a.DEFAULT_MANIFEST);r=a.read(m['receipt'])
   mutate(m,r,tmp)
   rf=tmp/'receipt.json';rf.write_text(json.dumps(r));m['receipt']=str(rf);m['receiptSha256']=a.sha(rf)
   mf=tmp/'manifest.json';mf.write_text(json.dumps(m))
   # Isolate receipt gate below the independently tested release pin.
   with patch.object(a,'ACCEPTED_MANIFEST_SHA256',a.sha(mf)):
    with self.assertRaises(ValueError):a.load_verified_manifest(mf)

 def test_ready_true_cannot_bypass_failed_overall_receipt(self):
  self._mutated_receipt(lambda m,r,t:r.update(passed=False))

 def test_failed_self_check_rejected_even_with_ready_and_passed(self):
  def mutation(m,r,tmp):
   f=tmp/'self.json';v=a.read(r['selfCheckReceipt']['file']);v['passed']=False;f.write_text(json.dumps(v))
   r['selfCheckReceipt']={'file':str(f),'sha256':a.sha(f)}
  self._mutated_receipt(mutation)

 def test_stale_source_rejected(self):
  self._mutated_receipt(lambda m,r,t:r['sourceHashes'].update({str(a.DEFAULT_MANIFEST):'0'*64}))

 def test_ascii_translation_and_bounds(self):
  with tempfile.TemporaryDirectory() as tmp:
   file=Path(tmp)/'triangle.stl';file.write_text('solid test\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid\n')
   p={'file':str(file),'key':'example','sha256':a.sha(file),'importTranslationMm':[2,3,4],
      'expectedFinalBoundsMm':[[2,3,4],[3,4,4]]}
   packed=a.packed_mesh(p,context=True)
   self.assertEqual(list(struct.iter_unpack('<3f',base64.b64decode(packed['positionB64']))),[(2,3,4),(3,3,4),(2,4,4)])
   self.assertEqual(packed['triangleCount'],1)

if __name__=='__main__':unittest.main()
