"""Specific carrier-first bench sequence; source retained blockers, bounded samples."""
import json,base64
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';sources=[Path(__file__)];cache=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((cache/'index.json').read_text());sources+=[cache/'index.json']
def read(p):
 sources.append(p);m=trimesh.load(p,force='mesh');assert m.is_watertight and m.is_volume;return g.conv(m)
def native(key):
 p=cache/idx['parts'][key];sources.append(p);r=json.loads(p.read_text());v=np.frombuffer(base64.b64decode(r['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(r['indexB64']),'<u4').reshape(-1,3);inputmesh=trimesh.Trimesh(v.copy(),f.copy(),process=True);s=mf.Manifold(mf.Mesh(np.asarray(inputmesh.vertices,np.float32),np.asarray(inputmesh.faces,np.uint32)));assert s.status()==mf.Error.NoError and s.volume()>0;mm=s.to_mesh64();tm=trimesh.Trimesh(mm.vert_properties[:,:3],mm.tri_verts,process=False);assert tm.is_watertight and tm.is_volume;return s
jaw=read(O/'jaw_support-split-channel-world.stl');carrier=read(O/'head_roll_bearing_carrier-split-channel-world.stl');main=read(O/'head_bottom-split-channel-world.stl');m15=native('motor15');ringa=native('head_roll_ring_a');ringb=native('head_roll_ring_b');m14=native('motor14');rows=[]
def route(name,moving,fixed,start,steps=121):
 row={'name':name,'startTranslationMm':start,'expectedPoses':steps,'completedPoses':0,'obstacles':list(fixed),'maximumIntersectionsMm3':{},'firstCollisions':[]};maxima={k:0 for k in fixed}
 for i,t in enumerate(np.linspace(1,0,steps)):
  move=moving.translate((np.array(start)*t).tolist())
  for k,b in fixed.items():
   h=move^b;assert h.status()==mf.Error.NoError;v=h.volume();maxima[k]=max(maxima[k],v)
   if v>1e-6 and not any(x['obstacle']==k for x in row['firstCollisions']):row['firstCollisions'].append({'obstacle':k,'sample':i,'translationMm':(np.array(start)*t).tolist(),'volumeMm3':v,'bounds':list(h.bounding_box())})
  row['completedPoses']+=1
 row['maximumIntersectionsMm3']=maxima;row['passed']=max(maxima.values())<=1e-6;rows.append(row);print(json.dumps(row),flush=True)
route('passive ring into loose carrier from above',ringb,{'carrier':carrier},[0,0,30])
route('carrier plus ring from below to loose jaw support',carrier+ringb,{'jaw_support':jaw},[0,0,-30])
# Passive ring must seat later axially, after carrier is positively keyed and screw02 retained.

route('main shell from below around completed central mechanism',main,{'jaw_support':jaw,'carrier':carrier,'motor15':m15,'motor14':m14,'ring_a':ringa,'ring_b':ringb},[0,0,-40],161)
# Screw02 is fastened at the detached carrier/jaw bench before motors close this access.
driver=mf.Manifold.cylinder(45,1.5,1.5,32).translate([49.1,9.35,114.0146]);tools={k:(driver^b).volume() for k,b in {'jaw_support':jaw,'carrier':carrier}.items()};report={'accepted':False,'rows':rows,'screw02DriverMm':{'diameter':3,'length':45,'intersectionsMm3':tools},'sourceHashes':{str(p):c.sha(p) for p in sources}};c.save(O/'split-carrier-assembly.json',report)
