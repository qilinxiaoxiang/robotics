from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
files={'holder':'imu-clamp-retained-world.stl','cover':'imu-cover-retained-world.stl','plug':'jst-sh4-receiving-world.stl'}
files.update({f'wire_{net}':f'imu_{net}-body-world.stl' for net in ['gnd','3v3','sda','scl']})
ms={};sol={};read=[]
for k,f in files.items():
 m=trimesh.load(D/f,force='mesh');assert m.is_volume,(k,m.is_watertight)
 s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));assert s.status()==mf.Error.NoError and not s.is_empty(),(k,s.status())
 ms[k]=m;sol[k]=s;read.append({'key':k,'volumeMm3':float(m.volume),'watertight':True,'bodyCount':len(m.split()),'boundsMm':m.bounds.tolist()})
nativeManifest=D/'bno-native-solids/manifest.json'
bj=json.loads(nativeManifest.read_text());boards=[]
for p in bj['solids']:
 m=trimesh.load(p['file'],force='mesh');assert m.is_volume,(p['index'],m.is_watertight)
 assert hashlib.sha256(Path(p['file']).read_bytes()).hexdigest()==p['sha256']
 a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));assert a.status()==mf.Error.NoError and not a.is_empty()
 boards.append(a)
sol['board']=mf.Manifold.batch_boolean(boards,mf.OpType.Add);assert sol['board'].status()==mf.Error.NoError
mb=sol['board'].to_mesh();whole=trimesh.Trimesh(mb.vert_properties[:,:3],mb.tri_verts,process=True);assert whole.is_volume
whole.export(D/'bno085-valid-native-world.stl')
read.append({'key':'board','nativeSolidInputs':len(boards),'validUnion':True,'volumeMm3':float(whole.volume),'boundsMm':whole.bounds.tolist()})
def iv(a,b):
 c=a^b;assert c.status()==mf.Error.NoError;return 0 if c.is_empty() else c.volume()
rows=[]
for title,moving,obstacles,axis,distance in [('board insertion','board',['holder'],0,25),('rear cover closure','cover',['holder','board','plug','wire_gnd','wire_3v3','wire_sda','wire_scl'],0,20),('SH plug insertion','plug',['holder'],1,12)]:
 for index in range(101):
  delta=[0.,0.,0.];delta[axis]=-distance*(1-index/100)
  a=sol[moving].translate(delta)
  for k in obstacles:rows.append({'operation':title,'sample':index,'translationMm':delta,'obstacle':k,'intersectionMm3':iv(a,sol[k])})
# Four original M2 rear-cover fasteners:3mm straight shaft approaches the head seat.
for y in [-17.5,17.5]:
 for z in [4,26]:
  tool=trimesh.creation.cylinder(radius=1.5,height=30,sections=32);T=np.eye(4);T[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]];T[:3,3]=[-77.6,y,z];tool.apply_transform(T)
  a=mf.Manifold(mf.Mesh(np.asarray(tool.vertices,dtype=np.float32),np.asarray(tool.faces,dtype=np.uint32)));assert a.status()==mf.Error.NoError
  for k in sol:rows.append({'operation':'rear M2 driver access','toolAxis':[1,0,0],'headSeatWorldMm':[-62.6,y,z],'obstacle':k,'intersectionMm3':iv(a,sol[k])})
# Source matching socket contacts intentionally are not probed using the enclosing plug box.
fail=[r for r in rows if r['intersectionMm3']>1e-7]
r={'scope':'BNO board seating, SH enclosure entrance, populated rear-cover closure; PCB held by original4-hole regions only','expectedChecks':941,'checks':rows,'complete':len(rows)==941,'meshReadback':read,'failures':fail,'passed':not fail,'sourceHashes':{str(D/f):hashlib.sha256((D/f).read_bytes()).hexdigest() for f in list(files.values())+['imu-retention.json','bno085-endpoint-registration.json','check_imu_assembly.py','bno-native-solids/manifest.json']},'matingExclusion':'Published SH housing receiving box is checked against enclosure only; it is not a native male mating surface. Manufacturer-listed SH family connection is retained.','physicalFitVerified':False}
(D/'imu-assembly-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'checks':len(rows),'failures':fail[:20],'failureCount':len(fail)}))
