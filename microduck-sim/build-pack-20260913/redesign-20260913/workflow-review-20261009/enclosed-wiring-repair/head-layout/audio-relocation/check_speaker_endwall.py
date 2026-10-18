import os,json,hashlib
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
O=Path(__file__).resolve().parent;D=O.parent;p=D/'native-cap-registered-world.stl';m=tm.load(p,force='mesh');mask=(m.face_normals[:,2]>.1)&(m.triangles[:,:,2].max(axis=1)>133.45);roof=m.submesh([np.flatnonzero(mask)],append=True,repair=False)
# True disk, including material boundary. Every disk point <=0.018mm from a sample.
pts=[]
for r in np.arange(0,1.05001,.025):
 for a in np.linspace(0,2*np.pi,max(1,int(np.ceil(2*np.pi*r/.025))),endpoint=False):pts.append([-16+r*np.cos(a),17+r*np.sin(a)])
rows=[]
for depth in [3.3,2.35]:
 q=np.column_stack((pts,np.full(len(pts),133.45+depth)));closest,d,tri=tm.proximity.closest_point(roof,q);i=int(np.argmin(d));rows.append({'pilotDepthMm':depth,'exactDiskSamplingMaxFillDistanceMm':.018,'minimumSampleEuclideanRoofDistanceMm':float(d[i]),'continuousDiskDistanceLowerBoundMm':max(0,float(d[i])-.018),'pointMm':q[i].tolist(),'closestOriginalExteriorMm':closest[i].tolist(),'outerNormal':roof.face_normals[tri[i]].tolist(),'pointCount':len(pts)})
out={'rows':rows,'source':str(p),'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Euclidean closest distance from circular blind-bore end disk to original upward exterior mesh; sample fill bound via1-Lipschitz distance. Vertical bore walls below end cannot approach this descending roof more closely in local single-valued roof region.'};(O/'speaker-endwall.json').write_text(json.dumps(out,indent=2));print(json.dumps(rows,indent=2))
