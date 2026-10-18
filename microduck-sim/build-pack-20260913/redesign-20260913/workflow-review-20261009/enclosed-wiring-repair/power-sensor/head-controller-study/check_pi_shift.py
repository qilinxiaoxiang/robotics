from pathlib import Path
import sys
SCOPE=sys.argv[1]
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
P=np.eye(4);P[:3,3]=[0,-8,2]
inv=read(HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json')
native=read(W/'enclosed-wiring-repair/ankle-wires/native-motors/manifest.json');nm=[q for q in native['parts']if q['motor']==2];G=read(W.parent/'leg-guide-20261006/full-build-data.json');gt={q['key']:np.array(q.get('sourceTransformWorld',np.eye(4)))for q in G['parts']};checks=[];fixed={};groups={k:'controller' for k in moving}
for row in inv['parts']:
 assert sha(row['file'])==row['sha256'];name=row['id'];motor=name.split()[-1]
 if name=='current_cap':
  path=W.parent/'head-redesign-20261008/curved-head/community-curved-head-world.stl';fixed['original_closed_cap']=solid(mesh(path),'original_closed_cap');continue
 if name=='current_amp':
  path=HD/'audio-relocation/original-controller-side/amplifier-quarter-turn-inset05-world.stl';moving['amp_side_candidate']=solid(mesh(path),'amp_side_candidate');groups['amp_side_candidate']='amp';continue
 if motor in ['motor13','motor14','motor15']:
  for q in nm:fixed[name+'/'+str(q['solid'])]=solid(mesh(q['file']),name+'/'+str(q['solid'])).transform((gt[motor]@np.linalg.inv(q['worldTransform']))[:3])
  continue
 o=mesh(row['file']);o.apply_transform(row['worldTransform']);v=solid(o,name)
 if name.startswith('REFERENCE Pi current') or name=='REFERENCE MicroB photo receiving':moving[name]=v.transform(P[:3]);groups[name]='pi'
 else:fixed[name]=v

def test(k,a,n,b):
 A=np.array(a.bounding_box()).reshape(2,3);B=np.array(b.bounding_box()).reshape(2,3)
 if np.any(A[1]<B[0])or np.any(B[1]<A[0]):return {'moving':k,'fixed':n,'method':'bounds-separated','volumeMm3':0}
 c=a^b;assert c.status()==mf.Error.NoError;v=max(0,c.volume());return {'moving':k,'fixed':n,'method':'individual-solid-intersection','volumeMm3':v,'intersectionBoundsMm':list(c.bounding_box())if v>1e-6 else None}
for k,a in moving.items():
 if groups[k]!='pi':continue
 for n,b in fixed.items():
  if (SCOPE=='cap' and n=='original_closed_cap') or (SCOPE=='fixed' and n!='original_closed_cap'):checks.append(test(k,a,n,b))
items=list(moving.items())
for i,(k,a) in enumerate(items):
 for n,b in items[i+1:]:
  if SCOPE=='coupled' and groups[k]!=groups[n] and 'pi' in [groups[k],groups[n]]:checks.append(test(k,a,n,b))
hits=[q for q in checks if q['volumeMm3']>1e-6];sums={}
for q in hits:
 key=q['fixed'].split('/')[0];sums[key]=sums.get(key,0)+q['volumeMm3']
report={'status':'ORIGINAL_CONTROLLER_CONTACT_DIRECTED_PI_SHIFT','accepted':not hits,'boardNativeToWorld':T.tolist(),'piCurrentWorldDelta':P.tolist(),'scopePart':SCOPE,'expectedPairs':sum(g=='pi' for g in groups.values())*(1 if SCOPE=='cap' else len(fixed)-1) if SCOPE!='coupled' else sum(groups[k]!=groups[n] and 'pi' in [groups[k],groups[n]]for i,(k,_)in enumerate(items)for n,_ in items[i+1:]),'completedPairs':len(checks),'checks':checks,'hits':hits,'sumIntersectionsByObstacleMm3':sums,'conservativeComponentHulls':conservative,'bounds':{k:list(v.bounding_box())for k,v in (moving|fixed).items()},'groups':groups,'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'retiredMounts':'Current added Pi/amp cap columns excluded; original untouched closed curved shell used. New mounts not designed. Speaker cradle remains included.','scope':'Static full rigid joint placement only, all142 controller components/full USB-C/twoEH plus all68 Pi parts/MicroB, camera/motors/originalshell/speaker/amp. No cable/installation acceptance.'}
(D/('original-controller-pi-shift-'+SCOPE+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'pairs':len(checks),'hits':len(hits),'byObstacle':sums},indent=2))
