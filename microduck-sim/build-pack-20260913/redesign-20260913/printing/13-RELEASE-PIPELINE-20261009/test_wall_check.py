"""Wall-thickness check tests: synthetic meshes, plus the prepare gate on the fixture manifest."""
import tempfile,unittest
from pathlib import Path
import numpy as np
import trimesh
import wall_check as w
import release_pipeline_v2 as r

def box(size,at=(0,0,0)):
 """Axis-aligned box with its minimum corner at `at`."""
 b=trimesh.creation.box(extents=size);b.apply_translation(np.array(at)+np.array(size)/2);return b
def union(*parts):return trimesh.boolean.union(parts,engine='manifold')
BASE=(10,10,5)
def finned(t):
 """10 x 10 x 5 mm block with a t x 5 x 5 mm fin standing on its top, centred."""
 return union(box(BASE),box((t,5,5),(5-t/2,2.5,5)))
FIN_BOX=[[4.,2.,4.5],[6.,8.,10.5]]   # holds the 0.6 mm fin (x 4.7-5.3, y 2.5-7.5, z 5-10) with margin

class MetricTests(unittest.TestCase):
 def test_plain_box_passes(self):
  c=w.check(box(BASE));self.assertTrue(c['passed'],c);self.assertEqual(c['regions'],[])
 def test_l_block_concave_corner_passes(self):
  m=union(box((10,10,4)),box((4,10,10)))   # L section, concave inner edge along y at x=4, z=4
  self.assertTrue(m.is_volume);c=w.check(m);self.assertTrue(c['passed'],c);self.assertEqual(c['regions'],[])
  m.apply_transform(trimesh.transformations.euler_matrix(.35,.5,.6));c=w.check(m)   # off-axis: tilted rays and triangle boxes
  self.assertTrue(c['passed'],c);self.assertEqual(c['regions'],[])
 def test_thin_fin_fails_and_region_covers_it(self):
  c=w.check(finned(.6),key='fin');self.assertFalse(c['passed']);self.assertEqual(len(c['failures']),1)
  reg=next(g for g in c['regions']if g['status']=='FAIL');(x0,y0,z0),(x1,y1,z1)=reg['bbox']
  self.assertTrue(4.<=x0<=4.7 and 5.3<=x1<=6.)                                  # the fin, plus its foot on the block top
  self.assertTrue(y0<=2.6 and y1>=7.4 and z0<=5.5 and z1>=9.5)
  self.assertGreaterEqual(reg['areaMm2'],w.MIN_REGION_MM2);self.assertAlmostEqual(reg['medianMm'],.6,delta=.05)
  self.assertIn('fin: wall thinner than 1.2 mm',c['failures'][0])
 def test_allowance_covers_the_fin_only_down_to_its_min(self):
  m=finned(.6)
  ok=w.check(m,w.allowances({'key':'fin','thinWallAllowances':[{'bbox':FIN_BOX,'minMm':.5,'reason':'test fin'}]}))
  self.assertTrue(ok['passed'],ok);self.assertEqual(ok['regions'][0]['status'],'allowed');self.assertEqual(ok['allowancesUsed'][0]['reason'],'test fin')
  low=w.check(m,w.allowances({'key':'fin','thinWallAllowances':[{'bbox':FIN_BOX,'minMm':.8,'reason':'test fin'}]}))
  self.assertFalse(low['passed']);self.assertEqual(low['allowancesUsed'],[])
  small=w.check(m,w.allowances({'key':'fin','thinWallAllowances':[{'bbox':[[4.,2.,4.5],[6.,5.,10.5]],'minMm':.5,'reason':'half'}]}))
  self.assertFalse(small['passed'])   # a box that holds only part of the region does not allow it
 def test_allowance_needs_bbox_min_and_reason(self):
  for e in ({'bbox':FIN_BOX,'minMm':.5},{'bbox':FIN_BOX,'minMm':1.2,'reason':'x'},{'bbox':[[0,0,0]],'minMm':.5,'reason':'x'},{'minMm':.5,'reason':'x'}):
   with self.assertRaises(AssertionError):w.allowances({'key':'fin','thinWallAllowances':[e]})
 def test_wall_of_1_5_mm_passes(self):
  c=w.check(finned(1.5));self.assertTrue(c['passed'],c);self.assertEqual(c['regions'],[])
  self.assertTrue(w.check(box((1.5,20,20)))['passed'])
 def test_bounded_rays_match_trimesh(self):
  m=finned(.6);p,f=trimesh.sample.sample_surface_even(m,3000,seed=1);d=-m.face_normals[f];o=p+d*1e-3
  loc,ir,_=m.ray.intersects_location(o,d,multiple_hits=False);ref=np.full(len(o),np.inf);np.minimum.at(ref,ir,np.linalg.norm(loc-o[ir],axis=1))
  self.assertLess(np.abs(w.first_hit(m,o,d)-np.minimum(ref,w.RAY_MAX_MM)).max(),1e-6)

class PrepareGateTests(unittest.TestCase):
 """The fixture manifest's single Black part swapped for a synthetic STL."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.m=r.read(r.HERE/'fixture-manifest.json')
 def tearDown(self):self.tmp.cleanup()
 def run_with(self,mesh,**row):
  stl=self.d/'part.stl';mesh.export(stl);self.m['parts'][0].update(path=str(stl),sha256=r.sha(stl),**row)
  p=self.d/'manifest.json';r.write(p,self.m);return r.prepare(p,self.d/'prepared')
 def test_thin_part_is_refused(self):
  with self.assertRaisesRegex(AssertionError,'pi_spacer_fixture: wall thinner than 1.2 mm'):self.run_with(finned(.6))
 def test_allowed_part_records_the_check(self):
  out=self.run_with(finned(.6),thinWallAllowances=[{'bbox':FIN_BOX,'minMm':.5,'reason':'test fin'}])
  wc=r.read(self.d/'prepared/preparation.json')['parts'][0]['wallCheck'];self.assertEqual(wc,out['parts'][0]['wallCheck'])
  self.assertTrue(wc['passed']);self.assertEqual(wc['allowancesUsed'][0]['reason'],'test fin');self.assertLess(wc['minSmoothedMm'],.7)
  self.assertEqual(r.source_receipt(self.d/'manifest.json')[1]['parts'],out['parts'])   # the recomputed check matches (verify)
 def test_spacer_fixture_passes(self):
  wc=r.prepare(r.HERE/'fixture-manifest.json',self.d/'prepared')['parts'][0]['wallCheck']
  self.assertTrue(wc['passed']);self.assertGreaterEqual(wc['minSmoothedMm'],w.MIN_WALL_MM)
 def test_legacy_marker_only_in_fixture_manifests(self):
  self.m['wallCheckLegacy']='printed before the wall rule'
  out=self.run_with(finned(.6));wc=out['parts'][0]['wallCheck'];self.assertFalse(wc['passed']);self.assertEqual(wc['legacy'],'printed before the wall rule')
  self.m['releaseKind']='incremental'
  with self.assertRaisesRegex(AssertionError,'only in fixture'):self.run_with(finned(.6))

if __name__=='__main__':unittest.main()
