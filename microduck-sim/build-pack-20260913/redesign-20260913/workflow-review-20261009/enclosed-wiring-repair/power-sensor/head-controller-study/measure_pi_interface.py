from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];H=W.parent/'head-redesign-20261008'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=D/'original-controller-pi-front-local-clearance-cap.json';j=json.loads(f.read_text());P=np.array(j['piCurrentWorldDelta']);path=H/'curved-head/community-curved-head-world.stl';m=trimesh.load_mesh(path);assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;s=s.transform(np.linalg.inv(P)[:3]);a=np.array([44,-9.9113773,133.6]);axis=P[:3,:3]@[-1,0,0]
def test(L):
 b=mf.Manifold.cube([L,13,6]).translate([44-L,-16.4113773,130.6]);c=b^s;assert c.status()==mf.Error.NoError;return max(0,c.volume())
lo=0;hi=25
for i in range(18):
 mid=(lo+hi)/2
 if test(mid)>1e-7:hi=mid
 else:lo=mid
rows=[{'bodyLengthMm':x,'intersectionMm3':test(x)}for x in [1,2,4,6,8,10,12,15,20,25]]
r={'scope':'Only fixed plug receiver cross-section axial cavity at dimension-directed joint board pose. No alternate connector or flexible cable accepted.','piCentreWorldMm':[59.2,0,128.7],'piCurrentWorldDelta':P.tolist(),'assumedMouldFrontPlaneCentreWorldMm':(P@np.r_[a,1])[:3].tolist(),'outwardAxisWorld':axis.tolist(),'crossSectionWidthAxisWorld':(P[:3,:3]@[0,1,0]).tolist(),'crossSectionThicknessAxisWorld':(P[:3,:3]@[0,0,1]).tolist(),'photoReceivingCrossSectionMm':[13,6],'currentAssumedBodyLengthMm':25,'contactBracketMm':[lo,hi],'samples':rows,'sourceHashes':{str(f):sha(f),str(path):sha(path),str(Path(__file__)):sha(__file__)},'notManufacturerMaximum':True,'engineeringConsequence':'A replacement body must turn its exit before this local closed-wall limit with adequate real assembly allowance; overall marketing dimensions alone do not establish connector mating datum or fit. Current straight receiving model fails.'}
(D/'pi-front-interface-measurements.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
