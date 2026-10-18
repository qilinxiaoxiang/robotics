from pathlib import Path
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;p=D/'coil-0.6-100.0-59.5.stl';m=trimesh.load(p,force='mesh');assert m.is_watertight;coil=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));start=np.array([62.9,-12.,124.]);pitch=.9;t=np.array([pitch/(2*np.pi),0,3.25]);t/=np.linalg.norm(t);w=np.array([0,1.,0]);n=np.cross(t,w);R=np.column_stack([w,n,t]);assert np.linalg.det(R)>0
rows=[]
for L in [4.,8.,12.]:
 # Start0.35mm away from adjacent coil end, so ordinary shared endpoint is excluded.
 T=np.eye(4);T[:3,:3]=R;T[:3,3]=start-t*(.35+L)/2
 lead=mf.Manifold.cube([16,.6,L-.35],True).transform(T[:3]);hit=lead^coil
 rows.append({'straightLeadFromInnerEndMm':L,'excludedAdjacentEndpointMm':.35,'overlapMm3':max(0.,float(hit.volume())),'intersectionBounds':hit.bounding_box() if hit.volume()>0 else None})
r={'integrationReady':False,'coil':str(p),'coilSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sameWidth16Thickness0p6':True,'innerEndFrame':{'position':start.tolist(),'tangent':t.tolist(),'widthAxis':w.tolist(),'contactNormal':n.tolist()},'rows':rows,'interpretation':'The ordinary tangential lead from the inner end intersects outer turns. This rejects a simple planar coil plus tangent tails; it does not prove all three-dimensional developable exits impossible. An axial exit would have to turn a16mm wide sheet out of the coil using a genuine developable fold/transition, not a free twisted rectangular sweep.'};(D/'coil-inner-exit-negative.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
