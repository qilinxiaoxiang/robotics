"""Conservative collision obstacle only; never a replacement board or print mesh."""
from pathlib import Path
import os,json,hashlib,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
from types import SimpleNamespace
from scipy.spatial import ConvexHull
D=Path(__file__).resolve().parent;H=D.parent.parent
source=H/'curved-head/openrb-curved-layout-world.stl';m=tm.load(source,force='mesh');v=m.vertices
h=ConvexHull(v);maximum=max(float(np.max(v@row[:3]+row[3])) for row in h.equations)
assert maximum<1e-9,maximum
proxy=m.convex_hull;assert proxy.is_watertight and proxy.is_volume
solid=mf.Manifold(mf.Mesh64(np.asarray(proxy.vertices,np.float64),np.asarray(proxy.faces,np.uint64)));assert solid.status()==mf.Error.NoError
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh
out=D/'openrb-conservative-convex-obstacle.stl';readback=precision_mesh.export(SimpleNamespace(np=np,tm=tm,mf=mf),solid,out)
report={'sourceFile':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sourceWatertight':bool(m.is_watertight),'sourceVertexCount':len(v),'halfspaceCount':len(h.equations),'allSourceVerticesEnclosed':True,'maximumHalfspaceViolationMm':maximum,'proxyFile':str(out),'proxySha256':hashlib.sha256(out.read_bytes()).hexdigest(),'readback':readback,'use':'Conservative collision obstacle only. Every original triangle is inside the convex hull of all its vertices; a zero overlap against this hull is sufficient for clearance, a positive overlap is inconclusive. This does not repair or certify the original board mesh and is never a viewer/print replacement.'}
(D/'openrb-conservative-enclosure.json').write_text(json.dumps(report,indent=2)+'\n');(D/'openrb-check-only-override.json').write_text(json.dumps({'openrb':str(out)},indent=2)+'\n');print(json.dumps(report))
