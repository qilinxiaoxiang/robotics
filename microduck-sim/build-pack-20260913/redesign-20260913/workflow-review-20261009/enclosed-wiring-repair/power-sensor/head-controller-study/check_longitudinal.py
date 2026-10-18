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
a=np.radians(10);T=np.eye(4);T[:3,:3]=[[0,np.cos(a),-np.sin(a)],[-1,0,0],[0,np.sin(a),np.cos(a)]];T[:3,3]=[22,-14,136]
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
inv=read(HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json');native=read(W/'enclosed-wiring-repair/ankle-wires/native-motors/manifest.json');nm=[q for q in native['parts']if q['motor']==2];G=read(W.parent/'leg-guide-20261006/full-build-data.json');gt={q['key']:np.array(q.get('sourceTransformWorld',np.eye(4)))for q in G['parts']};checks=[]; obs_info=[]
def test(k,a,n,b):
 A=np.array(a.bounding_box()).reshape(2,3);B=np.array(b.bounding_box()).reshape(2,3)
 if np.any(A[1]<B[0])or np.any(B[1]<A[0]):return {'moving':k,'fixed':n,'method':'bounds-separated','volumeMm3':0}
 c=a^b;assert c.status()==mf.Error.NoError;v=max(0,c.volume());return {'moving':k,'fixed':n,'method':'individual-solid-intersection','volumeMm3':v,'intersectionBoundsMm':list(c.bounding_box())if v>1e-6 else None}
for row in inv['parts']:
 assert sha(row['file'])==row['sha256'];name=row['id'];motor=name.split()[-1]
 if motor in ['motor13','motor14','motor15']:
  obs=[(name+'/'+str(q['solid']),solid(mesh(q['file']),name+'/'+str(q['solid'])).transform((gt[motor]@np.linalg.inv(q['worldTransform']))[:3]))for q in nm]
 else:
  o=mesh(row['file']);o.apply_transform(row['worldTransform']);obs=[(name,solid(o,name))]
 for n,b in obs:
  obs_info.append({'key':n,'boundsMm':list(b.bounding_box())})
  for k,a in moving.items():checks.append(test(k,a,n,b))
hits=[q for q in checks if q['volumeMm3']>1e-6];sums={}
for q in hits:
 key=q['fixed'].split('/')[0];sums[key]=sums.get(key,0)+q['volumeMm3']
report={'status':'ONE_SECTION_DERIVED_LONGITUDINAL_CANDIDATE','accepted':False,'boardNativeToWorld':T.tolist(),'sourceNativeBodies':len(nb),'sourceMeshConnectedComponents':len(subs),'allSourceTrianglesCoveredExactlyOnce':True,'sourceRepresentation':'Previously source-bound closed component convex enclosures; all source vertices included, so collision hits need actual component follow-up while zero proves separation.','sourceNativeBoundsMm':native_bounds,'combinedBoardBoundsMm':combined_bounds,'plugBoundsMm':{k:list(v.bounding_box())for k,v in moving.items()if not k.startswith('OpenRB')},'inventoryParts':len(inv['parts']),'sourceMotorComponentsReplaceInvalidLegacyMeshes':True,'expectedPairs':len(moving)*len(obs_info),'completedPairs':len(checks),'checks':checks,'hits':hits,'sumIntersectionsByObstacleMm3':sums,'conservativeComponentHulls':conservative,'obstacleBounds':obs_info,'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'scope':'All source OpenRB vertices plus complete USB-C mould/relief and two EH receivers against current90 head rigid inventory including MicroB. Invalid small mesh components conservatively convex-hulled; any hit involving those is receiving-body evidence, not exact physical overlap. No insertions, flexible routes or assembly acceptance.'}
(D/'longitudinal-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'nativeBounds':native_bounds,'boardBounds':report['combinedBoardBoundsMm'],'plugBounds':report['plugBoundsMm'],'components':len(subs),'conservative':conservative,'pairs':len(checks),'hitsByObstacle':sums},indent=2))
