from pathlib import Path
import sys
SCOPE=sys.argv[1]
import json,hashlib,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent;D=F.parent;W=D.parents[2];HD=W/'enclosed-wiring-repair/head-layout';SIM=W.parents[2];hashes={};conservative=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):hashes[str(p)]=sha(p);return json.loads(Path(p).read_text())
def mesh(p):hashes[str(p)]=sha(p);return trimesh.load_mesh(p)
def solid(m,label):
 if not m.is_volume:
  m=m.convex_hull;assert m.is_volume;conservative.append(label)
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
a=np.radians(-30);T=np.eye(4);T[:3,:3]=[[-np.sin(a),np.cos(a),0],[np.cos(a),np.sin(a),0],[0,0,-1]];T[:3,3]=[22,-3,139.5]
source=SIM/'hardware-design-20260912/whole-robot-20260912/electrical/sources/openrb-official.stl'
en=read(W.parent/'head-redesign-20261008/usb-access/usb-repair/openrb-component-enclosures/manifest.json');assert en['allSourceTrianglesCoveredExactlyOnce'];assert sha(en['sourceFile'])==en['sourceSha256']
reg=read(HD/'native-fusion-repair-inputs.json');old=np.array(reg['openrb']['nativeToCurrentWorld']);moving={}
for q in en['components']:
 assert sha(q['mesh'])==q['meshSha256'];moving['OpenRB_component_'+str(q['index'])]=solid(mesh(q['mesh']),'OpenRB_component_'+str(q['index'])).transform((T@np.linalg.inv(old))[:3]);conservative.append('OpenRB_component_'+str(q['index']))
actual=read(HD/'actual-openrb-components/micro-contact-proof.json');assert actual['sourceSha256']==en['sourceSha256']
for q in actual['records']:
 if q.get('mesh'):
  assert sha(q['mesh'])==q['meshSha256'];key='OpenRB_component_'+str(q['index']);m2=mesh(q['mesh']);assert m2.is_volume;moving[key]=solid(m2,key).transform((T@np.linalg.inv(old))[:3]);conservative.remove(key)
nb=read(SIM/'hardware-design-20260912/whole-robot-20260912/electrical/sources/openrb-solid-bounds.json');native_bounds=[np.min([q['bounds_mm'][0]for q in nb],axis=0).tolist(),np.max([q['bounds_mm'][1]for q in nb],axis=0).tolist()];subs=en['components'];combined_bounds=[np.min([np.array(v.bounding_box()).reshape(2,3)[0]for k,v in moving.items()if k.startswith('OpenRB')],axis=0).tolist(),np.max([np.array(v.bounding_box()).reshape(2,3)[1]for k,v in moving.items()if k.startswith('OpenRB')],axis=0).tolist()]
port=read(HD/'openrb-usbc-native-port.json');p=port['correctedAssumedMouldShoulderMm'];# native+Y USB axis
moving['C_mould22']=mf.Manifold.cube([12,22,7]).translate([p[0]-6,p[1],p[2]-3.5]).transform(T[:3])
moving['C_relief5']=mf.Manifold.cylinder(5,3.25/np.cos(np.pi/64),3.25/np.cos(np.pi/64),64).rotate([-90,0,0]).translate([p[0],p[1]+22,p[2]]).transform(T[:3])
reg=read(HD/'native-fusion-repair-inputs.json'); old=np.array(reg['openrb']['nativeToCurrentWorld']);ports=read(W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json')
for i,q in enumerate(ports['ports']):
 b=np.array(q['housingLocalBounds']);moving['EH_receiver_'+str(i)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform((T@np.linalg.inv(old)@np.array(q['transform']))[:3])

for q in read(D/'actual-pin-components.json')['records']:
 assert sha(q['file'])==q['sha256'];key='OpenRB_component_'+str(q['index']);moving[key]=solid(mesh(q['file']),key).transform((T@np.linalg.inv(old))[:3]);conservative.remove(key)
import gc
inv=read(HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json')
native=read(W/'enclosed-wiring-repair/ankle-wires/native-motors/manifest.json');nm=[q for q in native['parts']if q['motor']==2];G=read(W.parent/'leg-guide-20261006/full-build-data.json');gt={q['key']:np.array(q.get('sourceTransformWorld',np.eye(4)))for q in G['parts']}
checks=[];obstacles={}
def test(n,b):
 obstacles[n]=list(b.bounding_box());B=np.array(b.bounding_box()).reshape(2,3)
 for k,a in moving.items():
  A=np.array(a.bounding_box()).reshape(2,3)
  if np.any(A[1]<B[0])or np.any(B[1]<A[0]):checks.append({'moving':k,'fixed':n,'method':'bounds-separated','volumeMm3':0});continue
  c=a^b;assert c.status()==mf.Error.NoError;v=max(0,c.volume());checks.append({'moving':k,'fixed':n,'method':'solid','volumeMm3':v,'intersectionBoundsMm':list(c.bounding_box())if v>1e-6 else None})
for row in inv['parts']:
 name=row['id'];motor=name.split()[-1]
 if name.startswith('REFERENCE Pi current')or name=='REFERENCE MicroB photo receiving':continue
 if SCOPE=='cap' and name!='current_cap':continue
 if SCOPE=='fixed' and name=='current_cap':continue
 if name=='current_cap':v=solid(mesh(W.parent/'head-redesign-20261008/curved-head/community-curved-head-world.stl'),name);test('original_closed_cap',v)
 elif name=='current_amp':v=solid(mesh(HD/'audio-relocation/original-controller-side/amplifier-quarter-turn-inset05-world.stl'),name);test('side_amp',v)
 elif motor in ['motor13','motor14','motor15']:
  for q in nm:
   v=solid(mesh(q['file']),name).transform((gt[motor]@np.linalg.inv(q['worldTransform']))[:3]);test(name+'/'+str(q['solid']),v);del v;gc.collect()
  continue
 else:
  assert sha(row['file'])==row['sha256'];m=mesh(row['file']);m.apply_transform(row['worldTransform']);v=solid(m,name);test(name,v);del m
 del v;gc.collect()
hits=[q for q in checks if q['volumeMm3']>1e-6]
r={'accepted':False,'scope':'Controller plus full4472 and two EH static placement. Pi not yet checked. No installation acceptance.','sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'boardNativeToWorld':T.tolist(),'checks':checks,'hits':hits,'expectedPairs':len(moving)*len(obstacles),'completedPairs':len(checks),'bounds':{k:list(v.bounding_box())for k,v in moving.items()},'obstacles':obstacles,'conservative':conservative}
(F/('flipped-front-diagonal-'+SCOPE+'.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'count':len(checks),'hits':len(hits),'byObstacle':{n:sum(q['volumeMm3']for q in hits if q['fixed']==n)for n in set(q['fixed']for q in hits)}},indent=2))
