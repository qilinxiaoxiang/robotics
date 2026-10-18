"""Checkpointed physical per-wire channel subtraction. One part, bounded batches."""
import argparse,json,hashlib
from pathlib import Path
import short_path_worker as c
c.guard()
import flat_yaw_geometry as g
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-yaw-sweep';O.mkdir(exist_ok=True)
ap=argparse.ArgumentParser();ap.add_argument('--part',choices=['head_bottom','jaw_support'],required=True);ap.add_argument('--count',type=int,default=8);a=ap.parse_args()
man=H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';guidepath=H.parent/'leg-guide-20261006/full-build-data.json';guide=json.loads(guidepath.read_text());manifest=json.loads(man.read_text());rows=json.loads(g.w.BASE.read_text())['samples'];uniq={}
for i,r in enumerate(rows):
 if r['nativeShellOriginalBottomIntersectionsMm3']:continue
 q=r['jointDegrees'];key=(round(q.get('head_yaw',0),5),round(q.get('head_roll',0),5));uniq.setdefault(key,i)
poses=list(uniq.values())
if a.part=='head_bottom':src=H/manifest['replacementMeshes'][a.part];transform=None
else:
 p=next(p for p in guide['parts'] if p['key']==a.part);src=H.parents[2]/p['sourceFile'];transform=p['sourceTransformWorld']
inputs={str(p):c.sha(p) for p in [Path(__file__),D/'flat_yaw_geometry.py',src,man,guidepath,g.w.BASE,D/'low-voltage-neck-net-map.json',D/'rolling_loop_math.py']};meta=O/f'{a.part}.json';state=O/f'{a.part}.npz'
if meta.exists():
 r=json.loads(meta.read_text());assert r['sourceHashes']==inputs;assert c.sha(state)==r['stateSha256'];z=np.load(state);body=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));assert body.status()==mf.Error.NoError
else:
 m=trimesh.load(src,force='mesh');
 if transform:m.apply_transform(transform)
 body=g.conv(m);r={'accepted':False,'expectedUniqueHeadRelativePoses':poses,'completed':[],'details':[],'sourceHashes':inputs,'scope':'Channel occupancy only.79 unique yaw/roll transforms correspond186 native-clear source poses.43 native-blocked kept in domain report, not excused. No claim of all combined joint-domain continuum.'}
for i in poses[len(r['completed']):len(r['completed'])+a.count]:
 before=body.volume();specs=g.specs_for_pose(i);cuts=[]
 for s in specs:
  tube=g.tube(s['points'],s['receivingODMm']/2+.5);hit=tube^body;assert hit.status()==mf.Error.NoError
  if hit.volume()>1e-7:body=body-tube;assert body.status()==mf.Error.NoError
 assert body.volume()>0;r['completed'].append(i);r['details'].append({'pose':i,'removedMm3':before-body.volume(),'componentVolumesMm3':sorted([v.volume() for v in body.decompose()],reverse=True)})
 m=body.to_mesh64();np.savez(state,vertices=m.vert_properties[:,:3],faces=m.tri_verts);r['stateSha256']=c.sha(state);r['coverageComplete']=r['completed']==poses;r['remainingVolumeMm3']=body.volume();c.save(meta,r);print(json.dumps({'part':a.part,'pose':i,'completed':len(r['completed']),'expected':len(poses),'components':r['details'][-1]['componentVolumesMm3']}),flush=True)
