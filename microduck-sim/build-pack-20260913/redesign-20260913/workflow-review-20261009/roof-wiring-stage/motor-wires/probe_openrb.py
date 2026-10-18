from pathlib import Path
import numpy as np,trimesh,json
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
D=Path(__file__).resolve().parent;R=D.parents[2];M=R/'head-redesign-20261008/usb-access/usb-repair/openrb-component-enclosures/manifest.json';z=json.loads(M.read_text());m=trimesh.load_mesh(z['sourceFile'],process=True);v=np.asarray(m.vertices);f=np.asarray(m.faces)
rows=f[:,[0,1,2]].ravel();cols=f[:,[1,2,0]].ravel();n,l=connected_components(coo_matrix((np.ones(len(rows),np.int8),(rows,cols)),shape=(len(v),len(v))).tocsr(),directed=False)
normal=np.array([-.052335956,0,.998629535]);along=np.cross([0,1,0],normal)
ret={}
for ix in [60,82,74,110]:
 vv=v[l==ix];loc=np.array([vv@along,vv[:,1],vv@normal]).T
 unique,c=np.unique(np.round(loc[:,2],4),return_counts=True);vals=sorted(zip(unique.tolist(),c.tolist()),key=lambda x:-x[1])[:18]
 print(ix,'bounds',np.min(loc,axis=0),np.max(loc,axis=0),'zplanes',vals)
 ret[ix]={'bounds':np.array([loc.min(0),loc.max(0)]).tolist(),'zplanes':vals,'verts':loc.tolist()}
(D/'openrb-port-probe.json').write_text(json.dumps({'source':z['sourceFile'],'sourceSha256':z['sourceSha256'],'normal':normal.tolist(),'along':along.tolist(),'components':ret},indent=2))
