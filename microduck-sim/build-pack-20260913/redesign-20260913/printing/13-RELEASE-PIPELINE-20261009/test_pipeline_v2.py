"""Pipeline v2 per-object brim tests. The v1 tests (test_pipeline.py, test_binding.py) keep covering release_pipeline.py."""
import copy,json,sys,tempfile,unittest,zipfile
from pathlib import Path
import release_pipeline_v2 as r
ORIENT=Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/orientation-study')
ACCEPT=r.HERE/'tests/brim-per-object-V1.9-Orange'
V19=Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.9/run-r2')

class SettingsTests(unittest.TestCase):
 def test_r1_default_from_tip_angle(self):
  self.assertEqual(r.object_settings({'key':'a'},7.7)[0],r.R1_BRIM)
  self.assertEqual(r.object_settings({'key':'a'},10.0)[0],r.R1_NO_BRIM)
 def test_explicit_settings_need_reason(self):
  row={'key':'a','objectSettings':{'brim_type':'no_brim'}}
  with self.assertRaisesRegex(AssertionError,'objectSettingsReason'):r.object_settings(row,5)
  row['objectSettingsReason']='printed on a raft of its own';s,src=r.object_settings(row,5)
  self.assertEqual(s,{'brim_type':'no_brim'});self.assertTrue(src.startswith('manifest:'))
 def test_unsupported_or_incomplete_settings_rejected(self):
  for s in ({'brim_type':'inner_only','brim_width':'3','brim_object_gap':'0.1'},{'brim_type':'auto_brim'},{'brim_type':'outer_only'},
            {'brim_type':'no_brim','wall_loops':'3'},{'brim_type':'outer_only','brim_width':4,'brim_object_gap':'0.1'}):
   with self.assertRaises(AssertionError):r.object_settings({'key':'a','objectSettings':s,'objectSettingsReason':'x'},20)

class PrepareTests(unittest.TestCase):
 def setUp(self):self.m=r.read(r.HERE/'fixture-manifest.json');self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def run_manifest(self,m):p=self.d/'manifest.json';r.write(p,m);return r.prepare(p,self.d/'prepared')
 def test_plate_wide_brim_rejected(self):
  self.m['processOverrides']={'Black_Bambu':{'brim_type':'outer_only','brim_width':'4'}}
  with self.assertRaisesRegex(AssertionError,'per part'):self.run_manifest(self.m)
 def test_other_process_overrides_still_apply(self):
  self.m['processOverrides']={'Black_Bambu':{'wall_loops':'3'}};p=self.run_manifest(self.m)
  with zipfile.ZipFile(next(x for x in p['rows']if x['machine']=='Bambu')['project']['path'])as z:self.assertEqual(json.loads(z.read('Metadata/project_settings.config'))['wall_loops'],'3')
 def test_settings_written_per_object_and_recorded(self):
  self.m['parts'][0].update(objectSettings={'brim_type':'outer_only','brim_width':'3','brim_object_gap':'0.2'},objectSettingsReason='test')
  p=self.run_manifest(self.m);part=p['parts'][0]
  self.assertEqual(part['objectSettings']['brim_width'],'3');self.assertEqual(part['objectSettingsSource'],'manifest: test');self.assertEqual(p['pipelineVersion'],2)
  for row in p['rows']:
   with zipfile.ZipFile(row['project']['path'])as z:st=r.ET.fromstring(z.read('Metadata/model_settings.config'))
   md={m.get('key'):m.get('value')for m in st.find('object').findall('metadata')}
   self.assertEqual((md['brim_type'],md['brim_width'],md['brim_object_gap']),('outer_only','3','0.2'))
 def test_default_is_r1_and_matches_orientation_check(self):
  p=self.run_manifest(self.m);part=p['parts'][0];self.assertTrue(part['objectSettingsSource'].startswith('R1 default'))
  self.assertEqual(part['objectSettings'],r.R1_BRIM if part['tipAngleDeg']<10 else r.R1_NO_BRIM)
  sys.path.insert(0,str(ORIENT));import orientation_check as oc
  row=self.m['parts'][0];ref=oc.metrics(oc.load_mesh(Path(row['path'])),r.np.array(row['sourceToPrint'],float),[])['tipAngleDeg']
  self.assertAlmostEqual(part['tipAngleDeg'],ref,delta=.051)

def project(path,names):
 with zipfile.ZipFile(path,'w')as z:
  z.writestr('Metadata/project_settings.config',json.dumps({'initial_layer_print_height':.2}))
  z.writestr('Metadata/model_settings.config','<config>'+''.join(f'<object id="{i}"><metadata key="name" value="{n}"/></object>'for i,n in enumerate(names,1))+'<plate>'+''.join(f'<model_instance><metadata key="object_id" value="{i}"/><metadata key="identify_id" value="{100+i}"/></model_instance>'for i,_ in enumerate(names,1))+'</plate></config>')
 return path

class ColourOnlyReprintTests(unittest.TestCase):
 # Stock thigh community-74 (copy-manifest object 8) reprinted in another colour, as in V1.12.
 STOCK='/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/community-74.stl'
 def setUp(self):
  self.m=r.read(r.HERE/'fixture-manifest.json');self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
  row=self.m['parts'][0];row.update(key='thigh_fixture',path=self.STOCK,sha256=r.sha(self.STOCK),decision='replacement',replacesStockIds=['8'],
   sourceToPrint=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],flatContact={'minimumAreaMm2':1000})
 def tearDown(self):self.tmp.cleanup()
 def receipt(self):p=self.d/'manifest.json';r.write(p,self.m);return r.source_receipt(p)[1]
 def test_unchanged_stock_still_rejected_without_reason(self):
  with self.assertRaisesRegex(AssertionError,'Unchanged 89-stock'):self.receipt()
 def test_colour_only_reprint_of_exact_stock_accepted_and_counted(self):
  self.m['parts'][0]['colourOnlyReprint']='white instead of orange';rc=self.receipt()
  self.assertEqual(rc['reprintUnchangedStockQuantity'],1);self.assertEqual(rc['parts'][0]['colourOnlyReprint'],'white instead of orange')
 def test_colour_only_needs_the_replaced_instance_stl(self):
  self.m['parts'][0].update(colourOnlyReprint='white',replacesStockIds=['6'])  # community-72 instance, other bytes
  with self.assertRaisesRegex(AssertionError,'exact stock STL'):self.receipt()

class FirstLayerBrimTests(unittest.TestCase):
 # Orca layout: each object's brim printed before EXCLUDE_OBJECT_START, outside the label.
 G=(b'M83\nG1 X100 Y96 Z0.2\n;TYPE:Brim\n;WIDTH:0.4\nG1 X120 Y96 E1\nG1 X105 Y115\nG1 X115 Y115 E1\n'
    b'EXCLUDE_OBJECT_START NAME=u_1_id_0_copy_0\n;TYPE:External perimeter\nG1 X100 Y120\nG1 X100 Y100 E1\nG1 X120 Y100 E1\nG1 X120 Y120 E1\nEXCLUDE_OBJECT_END NAME=u_1_id_0_copy_0\n'
    b'EXCLUDE_OBJECT_START NAME=b_1_id_1_copy_0\n;TYPE:External perimeter\nG1 X160 Y100\nG1 X170 Y100 E1\nEXCLUDE_OBJECT_END NAME=b_1_id_1_copy_0\n')
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=project(Path(self.tmp.name)/'p.3mf',['u_1','b_1'])
 def tearDown(self):self.tmp.cleanup()
 def test_unlabelled_brim_goes_to_nearest_object(self):
  rows,fp=r.first_layer(self.G,self.p,'Elegoo');by={x['name']:x for x in rows}
  self.assertGreater(by['u_1']['brim_area_mm2'],0);self.assertEqual(by['b_1']['brim_area_mm2'],0)
  self.assertGreater(by['u_1']['brimInsideOwnHullMm2'],2)
  self.assertLessEqual(fp['allLayerModelSupportBrimBounds']['u_1'][1],95.8)   # brim joins the owner's footprint
 def test_reach_of_an_outer_brim(self):
  g=self.G.replace(b'G1 X105 Y115\nG1 X115 Y115 E1\n',b'');rows,_=r.first_layer(g,self.p,'Elegoo');u=next(x for x in rows if x['name']=='u_1')
  self.assertAlmostEqual(u['brimReachMm'],4.0,delta=.01)   # brim outer edge y 95.8 to model edge y 99.8;self.assertLess(u['brimInsideOwnHullMm2'],.01)
 def test_review_rules(self):
  rows,_=r.first_layer(self.G,self.p,'Elegoo')
  part=lambda k,s:dict(key=k,quantity=1,color='Orange',objectSettings=s)
  brim={'brim_type':'outer_only','brim_width':'4','brim_object_gap':'0.1'}
  out=r.brim_review(rows,[part('u',brim),part('b',r.R1_NO_BRIM)])
  self.assertFalse(out['objects']['u_1']['passed']);self.assertTrue(any('inside'in f for f in out['objects']['u_1']['failures']));self.assertTrue(out['objects']['b_1']['passed'])
  out=r.brim_review(rows,[part('u',r.R1_NO_BRIM),part('b',brim)])
  self.assertIn('unplanned',out['objects']['u_1']['failures'][0]);self.assertEqual(out['objects']['b_1']['failures'],['planned brim missing'])
  outer,_=r.first_layer(self.G.replace(b'G1 X105 Y115\nG1 X115 Y115 E1\n',b''),self.p,'Elegoo')
  self.assertTrue(r.brim_review(outer,[part('u',brim),part('b',r.R1_NO_BRIM)])['passed'])
  out=r.brim_review(outer,[part('u',dict(brim,brim_width='5')),part('b',r.R1_NO_BRIM)])   # slicer used 4 mm, plan says 5
  self.assertEqual(len(out['objects']['u_1']['failures']),1);self.assertIn('reach',out['objects']['u_1']['failures'][0])
  with self.assertRaisesRegex(AssertionError,'pipeline v1'):r.brim_review(rows,[dict(key='u',quantity=1),dict(key='b',quantity=1)])

@unittest.skipUnless((ACCEPT/'run/preparation.json').exists() and V19.exists(),'acceptance slices absent')
class RealSliceTests(unittest.TestCase):
 """Native slices: the delivered V1.9 Orange plate (plate-wide 4 mm brim) against the v2 plan, and the v2 scratch slice."""
 @classmethod
 def setUpClass(cls):
  sys.path.insert(0,str(r.HERE));import review_brim;cls.rb=review_brim;cls.plan=ACCEPT/'run/preparation.json'
 def test_v19_delivered_slice_fails_and_v2_slice_passes(self):
  for machine in r.MACHINES:
   old=self.rb.review(V19,'Orange',machine,self.plan);new=self.rb.review(ACCEPT/'run','Orange',machine)
   self.assertFalse(old['passed']);self.assertTrue(new['passed'])
   self.assertEqual(sorted(k for k,v in old['objects'].items()if not v['passed']),sorted(k for k in old['objects']if k!='head_cap_v19_1'))
   self.assertEqual([k for k,v in new['objects'].items()if v['brimAreaMm2']>0],['head_cap_v19_1'])
 def test_c_shaped_retainer_fails_even_when_brim_is_planned(self):
  plan=r.read(self.plan)
  for p in plan['parts']:
   if p['key']=='speaker_retainer_v19':p['objectSettings']=dict(r.R1_BRIM)
  with tempfile.TemporaryDirectory()as td:
   q=Path(td)/'plan.json';r.write(q,plan);out=self.rb.review(V19,'Orange','Bambu',q)['objects']['speaker_retainer_v19_1']
  self.assertFalse(out['passed']);self.assertGreater(out['brimInsideOwnHullMm2'],200);self.assertTrue(any('inside'in f for f in out['failures']))
@unittest.skipUnless((ACCEPT/'run/package-receipt.json').exists(),'packaged acceptance run absent')
class VerifyV2Tests(unittest.TestCase):
 def test_packaged_acceptance_run_verifies(self):
  import verify_release_v2 as v;out=v.verify(ACCEPT/'run');self.assertTrue(out['passed']);self.assertEqual(out['status'],'FIXTURE_ONLY_NOT_RELEASED')
 def test_v1_run_is_refused(self):
  import verify_release_v2 as v
  with self.assertRaisesRegex(AssertionError,'pipeline v2'):v.verify(r.HERE/'fixture-run')
 def test_edited_brim_review_is_rejected(self):
  import verify_release_v2 as v
  src=ACCEPT/'run';pkg=r.read(src/'package-receipt.json');idx=r.read(src/'delivery-index.json');checks=r.read(src/'native-delivery-checks.json')
  checks['checks'][0]['brimReview']['objects']['clip_cap_v19_1']['brimAreaMm2']=271.2
  with tempfile.TemporaryDirectory()as td:
   d=Path(td);r.write(d/'native-delivery-checks.json',checks);idx['nativeChecks']=r.ref(d/'native-delivery-checks.json');r.write(d/'delivery-index.json',idx)
   pkg['index']=r.ref(d/'delivery-index.json');r.write(d/'package-receipt.json',pkg)
   with self.assertRaisesRegex(AssertionError,'recomputed brim review'):v.verify(d)
if __name__=='__main__':unittest.main()
