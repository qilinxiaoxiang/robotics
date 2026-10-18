"""Proof-carrying conservative component obstacles, not replacement geometry."""
from pathlib import Path
import os,json,hashlib,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import ConvexHull,QhullError
from types import SimpleNamespace
D=Path(__file__).resolve().parent;H=D.parent.parent;out=D/'openrb-component-enclosures';out.mkdir(exist_ok=True)
source=H/'curved-head/openrb-curved-layout-world.stl';m=tm.load(source,force='mesh');v=m.vertices;f=m.faces
rows=f[:,[0,1,2]].ravel();cols=f[:,[1,2,0]].ravel();graph=coo_matrix((np.ones(len(rows),np.int8),(rows,cols)),shape=(len(v),len(v))).tocsr();count,labels=connected_components(graph,directed=False)
assert np.all(labels[f[:,0]]==labels[f[:,1]]) and np.all(labels[f[:,1]]==labels[f[:,2]])
faceLabels=labels[f[:,0]];del graph,rows,cols
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh
records=[]
for i in range(count):
 points=v[labels==i];triCount=int(np.sum(faceLabels==i));assert triCount
 try:
  hull=ConvexHull(points);maxOutside=max(float(np.max(points@q[:3]+q[3])) for q in hull.equations);assert maxOutside<1e-9
  proxy=tm.convex.convex_hull(points);kind='convex_hull'
 except QhullError:
  lo=points.min(axis=0)-1e-5;hi=points.max(axis=0)+1e-5;proxy=tm.creation.box(hi-lo,transform=tm.transformations.translation_matrix((hi+lo)/2));maxOutside=0.;kind='padded_degenerate_component_aabb'
 assert proxy.is_watertight and proxy.is_volume
 solid=mf.Manifold(mf.Mesh64(np.asarray(proxy.vertices,np.float64),np.asarray(proxy.faces,np.uint64)));assert solid.status()==mf.Error.NoError
 path=out/f'component-{i:04d}.stl';back=precision_mesh.export(SimpleNamespace(np=np,tm=tm,mf=mf),solid,path)
 records.append({'index':i,'sourceTriangleCount':triCount,'sourceVertexCount':len(points),'sourceVertexSetSha256':hashlib.sha256(np.ascontiguousarray(points).tobytes()).hexdigest(),'bounds':proxy.bounds.tolist(),'kind':kind,'maximumHalfspaceViolationMm':maxOutside,'mesh':str(path),'meshSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'readback':back})
assert sum(x['sourceTriangleCount'] for x in records)==len(f)
r={'sourceFile':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sourceTriangleCount':len(f),'allSourceTrianglesCoveredExactlyOnce':True,'componentCount':count,'components':records,'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rule':'Each original triangle is wholly contained in its connected component convex hull; degenerate components use an enclosing AABB expanded1e-5mm. All component obstacles must clear. No board shape is replaced or source defect waived.'}
(out/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'components':count,'triangles':len(f),'largestComponentTriangles':max(x['sourceTriangleCount'] for x in records)}))
