"""Source/sequence regression; no CAD or full HTML generation."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
import build_head_prototype_adapter as A

class HeadPrototypeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base=json.loads((A.G/'full-build-data.json').read_text())
  cls.wire=json.loads((A.G/'wiring-guide-data.json').read_text())
  cls.spatial=json.loads((A.G/'wiring-spatial-data.json').read_text())
  cls.parts,cls.adopt,cls.refs=A.load_current_parts()
  with patch.object(A,'load_current_parts',return_value=(cls.parts,cls.adopt,cls.refs)):
   cls.data,cls.w,cls.sp=A.apply_head_prototype_adapter(cls.base,cls.wire,cls.spatial)
 def test_nonhead_modules_unchanged(self):
  self.assertEqual([m for m in self.base['modules'] if m['id'] not in A.HEAD_MODULES],[m for m in self.data['modules'] if m['id'] not in A.HEAD_MODULES])
 def test_source_not_mutated(self):
  self.assertNotIn('headPrototypeRevision',self.base)
  self.assertNotIn('prototypeFitPending',self.wire['connections'][0])
 def test_new_source_geometry(self):
  parts={p['key']:p for p in self.data['parts']}
  for key in ['head_cap','head_bottom','face_panel','speaker_cradle','speaker_keeper','camera_retainer','eye_trim','mouth_sliding_ring']:
   self.assertEqual(A.sha(parts[key]['sourceFile']),parts[key]['sha256'])
  self.assertEqual(parts['head_cap']['sha256'],'d86ae8b6fe787b8208d99ab4a22da188545ec55556eac4b8c00dcd2cfd0cda97')
  self.assertEqual(parts['head_bottom']['sha256'],'276f36f6991eeb631b9b9ac340fedb7a522906bfa59a55e8d03c33ab5142e10b')
 def test_no_obsolete_parts_or_screws(self):
  keys={p['key'] for p in self.data['parts']}
  for key in ['camera_pitch_foot','camera_cradle','audio_carrier','nut_E-openrb-01','nut_E-camera_foot-01']:
   self.assertNotIn(key,keys)
  self.assertFalse(any('pi_spacer' in k or '2187' in k or '1826' in k for k in keys))
  self.assertFalse(any(s['id'].startswith(('E-pi-','E-openrb-','E-audio_carrier-','E-camera_')) for s in self.data['screws']))
 def test_complete_module_references(self):
  keys={p['key'] for p in self.data['parts']}
  for m in self.data['modules']:
   if m['id'] not in A.HEAD_MODULES:continue
   self.assertFalse(set(m['partKeys'])-keys)
   self.assertFalse(set(m['ownedPartKeys'])-keys)
   for op in m['operations']:
    self.assertFalse(set(op['visiblePartKeys'])-keys)
    self.assertFalse(set(op['add'])-keys)
    self.assertIn('animationBlockedReason',op)
    self.assertNotIn('motionStop',op)
    self.assertNotIn('requiresPhysicalFit',op) # cannot dispatch stale CLOSURE paths
 def test_preconnection_and_pending_usb(self):
  modules={m['id']:m for m in self.data['modules']}
  camera=modules['camera']['operations']
  self.assertIn('ribbon',camera[1]['title'])
  self.assertIn('Retain',camera[2]['title'])
  text=' '.join(o['text'] for o in modules['electronics']['operations'])
  self.assertIn('before',text)
  self.assertIn('4472',text)
  self.assertFalse(self.data['headPrototypeRevision']['finishedUsbCableSelected'])
  self.assertFalse(self.data['headPrototypeRevision']['wholeHeadAccepted'])
 def test_no_stale_route_animation(self):
  for c in self.sp['connections']:
   if c.get('prototypeFitPending'):self.assertEqual(c['segments'],[])
  js=(A.G/'wiring3d.js').read_text()
  self.assertIn("if(wireCurrent?.prototypeFitPending&&wireMode!=='header'){renderHeadPrototypeContext();return;}",js)
  self.assertIn("host.dataset.wireTubeCount='0'",js)
 def test_leg_routes_unchanged(self):
  old={c['id']:c for c in self.spatial['connections'] if c['id'].startswith('ttl-')}
  new={c['id']:c for c in self.sp['connections'] if c['id'].startswith('ttl-')}
  self.assertEqual(old,new)
 def test_unrelated_spatial_cables_preserved(self):
  sp=copy.deepcopy(self.spatial)
  body={'key':'body_test_lead','wiringRole':'cable','moduleId':'power','proof':'unchanged'}
  imu={'key':'imu_test_lead','wiringRole':'cable','moduleId':'imu','proof':'unchanged'}
  sp['currentParts']=[body,imu,{'key':'camera_ribbon_200','wiringRole':'cable'}]
  with patch.object(A,'load_current_parts',return_value=(self.parts,self.adopt,self.refs)):
   _,_,out=A.apply_head_prototype_adapter(self.base,self.wire,sp)
  self.assertIn(body,out['currentParts']);self.assertIn(imu,out['currentParts'])
  self.assertNotIn('camera_ribbon_200',{p['key'] for p in out['currentParts']})
 def test_one_internal_usb_link(self):
  self.assertNotIn('openrb-usb',{c['id'] for c in self.w['connections']})
  c=next(c for c in self.w['connections'] if c['id']=='pi-otg')
  self.assertEqual(c['to'],'OpenRB USB-C device port')
 def test_incident_endpoints_not_id_allowlist(self):
  w=copy.deepcopy(self.wire);sp=copy.deepcopy(self.spatial)
  c={'id':'future-pi-5v','fromNodeIds':['body-open'],'toNodeIds':['pi'],'purpose':'5 V'}
  w['connections'].append(c)
  sp['connections'].append({'id':'future-pi-5v','segments':[{'from':'body-open','to':'pi'}]})
  body={'id':'body-open-only','segments':[], 'checkedHarnessRoute':{'contextPartKeys':['pi'],'endpoints':[]}}
  sp['connections'].append(body)
  with patch.object(A,'load_current_parts',return_value=(self.parts,self.adopt,self.refs)):
   _,ww,out=A.apply_head_prototype_adapter(self.base,w,sp)
  self.assertTrue(next(c for c in ww['connections'] if c['id']=='future-pi-5v')['prototypeFitPending'])
  self.assertEqual(next(c for c in out['connections'] if c['id']=='future-pi-5v')['segments'],[])
  self.assertEqual(next(c for c in out['connections'] if c['id']=='body-open-only'),body)
 def test_every_actual_head_incident_edge_is_retired(self):
  ids=A.moved_head_connection_ids(self.wire,self.spatial)-{'openrb-usb','pi-gnd-6','pi-gnd-14','audio-return'}
  current={c['id']:c for c in self.sp['connections']}
  for id in ids:
   self.assertTrue(current[id]['prototypeFitPending'],id)
   self.assertEqual(current[id]['segments'],[],id)
  self.assertIn('data-01',ids)
 def test_head_power_destinations_complete_without_duplicate_returns(self):
  connections={c['id']:c for c in self.w['connections']}
  for old in ['pi-gnd-6','pi-gnd-14','audio-return']:self.assertNotIn(old,connections)
  pi=connections['head-pi-supply']
  self.assertEqual({p['to'] for p in pi['pins']},{'physical 2','physical 4','physical 6','physical 14'})
  self.assertIn('22 AWG',pi['wire'])
  board=connections['head-openrb-supply']
  self.assertEqual({p['to'] for p in board['pins']},{'J4 VIN+','J4 GND'})
  self.assertIn('VIN(DXL)',' '.join(board['tutorial']['assemble']))
  self.assertEqual(connections['head-amplifier-vin']['pins'][0]['to'],'VIN')
  self.assertIn('return',connections['audio-20']['purpose'])
  for id in ['head-pi-supply','head-openrb-supply','head-amplifier-vin']:
   c=next(c for c in self.sp['connections'] if c['id']==id)
   self.assertEqual(c['segments'],[]);self.assertTrue(c['prototypeFitPending'])
  self.assertFalse(self.data['headPrototypeRevision']['headPowerInstructions']['headDistributionTerminationSelected'])
 def test_head_power_step_does_not_shift_other_steps(self):
  before=[s['id'] for s in self.wire['steps']]
  after=[s['id'] for s in self.w['steps']]
  self.assertEqual(after[:len(before)],before)
  self.assertEqual(after[-1],'head-power-current')
 def test_bundle_order(self):
  text=(A.G/'bundle_guide.py').read_text()
  self.assertLess(text.index('data,wiring,spatial=apply_input_wiring_adapter'),text.index('data,wiring,spatial=apply_head_prototype_adapter'))
 def test_source_tamper_rejected(self):
  bad=dict(next(p for p in self.parts if p['key']=='head_cap'))
  with self.assertRaises(ValueError):A.check_ref({'file':bad['sourceFile'],'sha256':'0'*64})

if __name__=='__main__':unittest.main()
