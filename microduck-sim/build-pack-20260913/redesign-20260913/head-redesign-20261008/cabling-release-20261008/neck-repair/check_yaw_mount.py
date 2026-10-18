"""One current candidate mesh obstacle. No unrelated parts loaded."""
import argparse,json
from pathlib import Path
import segmented_yaw_forward_worker as w
w.core.guard()
import numpy as np,trimesh,manifold3d as mf
from segment_capsule_clearance import check
ap=argparse.ArgumentParser();ap.add_argument('--pose',type=int,required=True);ap.add_argument('--key',required=True);o=ap.parse_args();w.current();s=json.loads((w.OUT/'self-summary.json').read_text());assert s['passed'] and s['planHash']==w.sha(w.OUT/'plan.json')
man=w.H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';d=json.loads(man.read_text());sourceData=w.H.parent/'leg-guide-20261006/full-build-data.json';part=next(x for x in json.loads(sourceData.read_text())['parts'] if x['key']==o.key);mp=w.H.parents[2]/part['sourceFile']
# Bind full current manifest and actual selected mesh, do not infer integration acceptance.
import base64
mesh=trimesh.load(mp,force='mesh',process=True);mesh.apply_transform(np.asarray(part['sourceTransformWorld']))
solid=mf.Manifold(mf.Mesh(np.array(mesh.vertices,np.float32),np.array(mesh.faces,np.uint32)));assert solid.status()==mf.Error.NoError and solid.volume()>0
normalization=None
if not (mesh.is_watertight and mesh.is_volume):
 import hashlib
 def digest(m):
  triangles=np.ascontiguousarray(m.vertices[m.faces],dtype=np.float32);vertices=np.sort(triangles.view('V12').reshape(-1,3),axis=1);return hashlib.sha256(np.sort(vertices.view('V36').reshape(-1)).tobytes()).hexdigest()
 before=digest(mesh);fixed=solid.to_mesh();nm=trimesh.Trimesh(fixed.vert_properties[:,:3],fixed.tri_verts,process=False);assert nm.is_watertight and nm.is_volume and digest(nm)==before and np.array_equal(nm.bounds,mesh.bounds)
 normalization={'rule':'Split coincident contact vertices only; triangle coordinate multiset unchanged','triangleMultisetSha256':before};mesh=nm
assert mesh.is_watertight and mesh.is_volume

row,g=w.route(o.pose);q=row['jointDegrees'];origin=np.array(w.moved([0,0,0],q));rot=np.array([w.moved(e,q,True) for e in [[1,0,0],[0,1,0],[0,0,1]]]).T;solid=solid.transform(np.column_stack([rot,origin]));r=check(g['points'],3.5,w.SAGITTA,solid,source_evidence={'watertight':True,'positiveVolume':True,'sourceSha256':w.sha(mp)});r.update(pose=o.pose,key=o.key,body='jaw_soft',topologyNormalization=normalization,planHash=w.sha(w.OUT/'plan.json'),candidateManifestHash=w.sha(man),candidateIntegrationReady=d['integrationReady'],sourceHashes={str(p):w.sha(p) for p in [Path(__file__),man,mp,sourceData,w.OUT/'plan.json']});w.save(w.OUT/'candidate-pairs'/f'{o.pose}__{o.key}.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['segments','sourceHashes']}));raise SystemExit(0 if r['passed'] else 2)
