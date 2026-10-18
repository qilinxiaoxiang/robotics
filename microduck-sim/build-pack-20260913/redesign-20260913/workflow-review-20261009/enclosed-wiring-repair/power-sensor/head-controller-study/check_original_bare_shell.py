from pathlib import Path

import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];HD=W/'enclosed-wiring-repair/head-layout';SIM=W.parents[2];hashes={};conservative=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):hashes[str(p)]=sha(p);return json.loads(Path(p).read_text())
def mesh(p):hashes[str(p)]=sha(p);return trimesh.load_mesh(p)
def solid(m,label):
 if not m.is_volume:
  m=m.convex_hull;assert m.is_volume;conservative.append(label)
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
T=np.array(read(HD/'native-fusion-repair-inputs.json')['openrb']['nativeToCurrentWorld'])
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

capfile=W.parent/'head-redesign-20261008/curved-head/community-curved-head-world.stl';cap=solid(mesh(capfile),'original_closed_cap');checks=[]
for k,a in moving.items():
 A=np.array(a.bounding_box()).reshape(2,3);B=np.array(cap.bounding_box()).reshape(2,3)
 if np.any(A[1]<B[0])or np.any(B[1]<A[0]):v=0;method='bounds-separated'
 else:
  c=a^cap;assert c.status()==mf.Error.NoError;v=max(0,c.volume());method='valid-solid-intersection'
 checks.append({'part':k,'volumeMm3':v,'method':method})
r={'scope':'Complete original controller plus requiredC22/relief5 andtwoEH versus original closed curve. No new mount or wire acceptance.','expectedPairs':146,'completedPairs':len(checks),'checks':checks,'nativePCBAndComponentSubsetClear':not any(q['volumeMm3']>1e-6 for q in checks if q['part'].startswith('OpenRB')),'completeInterfaceClear':not any(q['volumeMm3']>1e-6 for q in checks),'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)}}
assert len(checks)==146
(D/'original-controller-bare-shell-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([q for q in checks if q['volumeMm3']>1e-6],indent=2))
