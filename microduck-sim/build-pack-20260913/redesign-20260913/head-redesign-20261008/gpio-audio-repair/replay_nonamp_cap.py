#!/usr/bin/env python3
"""Replay source construction without ever adding original amplifier posts.

No CAD runs until parent grants token and run_bounded_cad.py sets environment.
Original cap geometry and exact existing service/rail cut inputs are retained.
"""
import json,gc
from pathlib import Path
import unify_amp_cap as u


def main():
 u.require_classification();u.core.guarded_import();c=u.core
 basefile=u.K/'curved-cap-with-internal-posts-and-usb-world.stl';railfile=u.K/'internal-rail-relief-removed-world.stl';usbfile=u.H/'usb-access/openrb-usb-c-receiving-world.stl';usbmeta=u.H/'usb-access/usb-report.json'
 bindings=u.inputs([Path(__file__),basefile,railfile,usbfile,usbmeta]);report={'method':'Replay source OpenRB cap plus exact speaker-post components, original service/rail cuts; omit original amplifier posts at construction.','inputHashes':bindings,'integrationReady':False,'steps':[]}
 out=u.OUT/'nonamp-replay-attempt.json'
 def checkpoint(step):
  report['steps'].append(step);c.atomic_json(out,report)
 cap=u.load(basefile);audio=u.load(u.AUDIO);parts=audio.decompose();assert len(parts)==4
 speakers=[];amps=[]
 for part in parts:
  bb=list(part.bounding_box());mid=[(bb[i]+bb[i+3])/2 for i in range(3)]
  if mid[0]<0:speakers.append(part)
  else:amps.append(part)
 assert len(speakers)==2 and len(amps)==2
 # The two speaker components are selected whole from their source artifact;
 # no intersection/cutter ever touches original roof or OpenRB geometry here.
 for p in speakers:cap=cap+p
 checkpoint('source-openrb-cap-and-two-whole-speaker-posts')
 del audio,parts,amps,speakers;gc.collect()
 usb=u.load(usbfile);axis=json.loads(usbmeta.read_text())['outwardAxis'];shift=[float(v)*30 for v in axis]
 usbcut=c.mf.Manifold.batch_hull([usb,usb.translate(shift)]).minkowski_sum(c.mf.Manifold.cube([1,1,1],center=True));cap=cap-usbcut
 checkpoint('original-source-usb-c-cut');del usb,usbcut;gc.collect()
 rail=u.load(railfile);cap=cap-rail;checkpoint('exact-original-source-rail-removal');del rail;gc.collect()
 # Same numerical simplification bound as the original finalized cap source.
 cap=cap.simplify(.00003);candidate=u.OUT/'cap-nonamp-replay-candidate-world.stl'
 q=cap.to_mesh64();mesh=c.tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);report.update(watertight=bool(mesh.is_watertight),windingConsistent=bool(mesh.is_winding_consistent),triangles=len(mesh.faces));checkpoint('stl-precision-topology-screen')
 if not mesh.is_watertight:raise ValueError('Replay still not watertight; no accepted output')
 with candidate.open('w') as f:
  f.write('solid nonamp_cap\n')
  for normal,triangle in zip(mesh.face_normals,mesh.triangles):
   f.write(' facet normal '+' '.join(repr(float(x)) for x in normal)+'\n  outer loop\n')
   for v in triangle:f.write('   vertex '+' '.join(repr(float(x)) for x in v)+'\n')
   f.write('  endloop\n endfacet\n')
  f.write('endsolid nonamp_cap\n')
 del mesh,q,cap;gc.collect();read=c.tm.load(candidate,force='mesh');assert read.is_watertight
 cap=c.mf.Manifold(c.mf.Mesh64(c.np.asarray(read.vertices,c.np.float64),c.np.asarray(read.faces,c.np.uint64)));assert cap.status()==c.mf.Error.NoError
 report['exportFormat']='ASCII STL with round-trip float64 vertex text; no face deletion, no hole filling';report['readbackWatertight']=bool(read.is_watertight);del read;gc.collect()
 original=u.load(u.BASE);native=u.load(u.NATIVE);old,speaker=u.old_amp_features(native);removed=original-cap;tests={'nativeSkinRemovedMm3':u.vol(removed^native),'speakerRemovedMm3':u.vol(removed^speaker),'unexpectedRemovedMm3':u.vol(removed-old),'addedMm3':u.vol(cap-original)}
 del speaker;gc.collect();openrb=u.load(u.OPENRB);tests['openrbRemovedMm3']=u.vol(removed^openrb);del openrb;gc.collect();report['readbackChecks']=tests;report['outputSha256']=c.sha(candidate);report['passed']=all(v<1e-4 for v in tests.values());checkpoint('readback-material-preservation')
 print(json.dumps({k:v for k,v in report.items() if k not in ['inputHashes']}));assert report['passed'],tests
 # Keep diagnostic candidate separate. Parent can authorize promoting this
 # receipt/mesh to the staged retire output after independent review.
if __name__=='__main__':main()
