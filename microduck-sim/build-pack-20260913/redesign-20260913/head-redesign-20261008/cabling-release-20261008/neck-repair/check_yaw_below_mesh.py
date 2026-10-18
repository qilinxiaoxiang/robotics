"""One current candidate mesh obstacle. No unrelated parts loaded."""
import argparse,json
from pathlib import Path
import segmented_yaw_below_worker as w
w.core.guard()
import numpy as np,trimesh,manifold3d as mf
from segment_capsule_clearance import check
ap=argparse.ArgumentParser();ap.add_argument('--pose',type=int,required=True);ap.add_argument('--key',required=True);o=ap.parse_args();w.current();s=json.loads((w.OUT/'self-summary.json').read_text());assert s['passed'] and s['planHash']==w.sha(w.OUT/'plan.json')
man=w.H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';d=json.loads(man.read_text());mp=w.H/d['replacementMeshes'][o.key];bound=next((h for f,h in d['sourceHashes'].items() if Path(f).resolve()==mp.resolve() or (w.H/f).resolve()==mp.resolve()),None)
# Bind full current manifest and actual selected mesh, do not infer integration acceptance.
mesh=trimesh.load(mp,force='mesh',process=True);valid=bool(mesh.is_watertight and mesh.is_volume);assert valid,'Invalid input mesh cannot establish clearance';solid=mf.Manifold(mf.Mesh(np.array(mesh.vertices,np.float32),np.array(mesh.faces,np.uint32)));assert solid.status()==mf.Error.NoError and solid.volume()>0
row,g=w.route(o.pose);q=row['jointDegrees'];origin=np.array(w.moved([0,0,0],q));rot=np.array([w.moved(e,q,True) for e in [[1,0,0],[0,1,0],[0,0,1]]]).T;solid=solid.transform(np.column_stack([rot,origin]));r=check(g['points'],3.5,w.SAGITTA,solid,source_evidence={'watertight':True,'positiveVolume':True,'sourceSha256':w.sha(mp)});r.update(pose=o.pose,key=o.key,body='jaw_soft',planHash=w.sha(w.OUT/'plan.json'),candidateManifestHash=w.sha(man),candidateIntegrationReady=d['integrationReady'],sourceHashes={str(p):w.sha(p) for p in [Path(__file__),man,mp,w.OUT/'plan.json']});w.save(w.OUT/'candidate-pairs'/f'{o.pose}__{o.key}.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['segments','sourceHashes']}));raise SystemExit(0 if r['passed'] else 2)
