"""One obstacle, explicit body3/body4 relationship, eleven roll states."""
import argparse,json,base64
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'guide-clips';ap=argparse.ArgumentParser();ap.add_argument('--key',required=True);ap.add_argument('--mesh');ap.add_argument('--fixed',action='store_true');a=ap.parse_args();paths=[Path(__file__)];moving=[]
cache=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((cache/'index.json').read_text());p=cache/idx['parts']['motor13'];paths.extend([p,cache/'index.json']);j=json.loads(p.read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(j['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(j['indexB64']),'<u4').reshape(-1,3),process=True);ss=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert ss.status()==mf.Error.NoError and ss.volume()>0;moving=[('motor13',ss)]

if a.mesh:p=Path(a.mesh);ob=g.conv(trimesh.load(p,force='mesh'));paths.append(p)
else:
 cache=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((cache/'index.json').read_text());p=cache/idx['parts'][a.key];paths.extend([p,cache/'index.json']);j=json.loads(p.read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(j['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(j['indexB64']),'<u4').reshape(-1,3),process=True);ob=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert ob.status()==mf.Error.NoError and ob.volume()>0;nm=ob.to_mesh64();t=trimesh.Trimesh(nm.vert_properties[:,:3],nm.tri_verts,process=False);assert t.is_watertight and t.is_volume
rows=[]
for angle in ([0] if a.fixed else range(-25,26,5)):
 b=ob if a.fixed else ob.translate([-8.1,0,-115.6146]).rotate([-angle,0,0]).translate([8.1,0,115.6146]);hits={}
 for k,s in moving:
  v=s^b;assert v.status()==mf.Error.NoError
  if v.volume()>1e-8:hits[k]={'volumeMm3':v.volume(),'bounds':list(v.bounding_box())}
 rows.append({'roll':angle,'hits':hits})
r={'passed':all(not x['hits'] for x in rows),'key':a.key,'expectedRollStates':1 if a.fixed else 11,'completedRollStates':len(rows),'rows':rows,'sourceHashes':{str(p):c.sha(p) for p in paths}};c.save(O/f'baseline-motor13-roll-{a.key}.json',r);print(json.dumps(r))
