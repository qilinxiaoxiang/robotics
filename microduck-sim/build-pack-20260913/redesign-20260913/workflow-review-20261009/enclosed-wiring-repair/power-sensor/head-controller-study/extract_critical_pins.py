from pathlib import Path
import json,hashlib,numpy as np,trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
D=Path(__file__).resolve().parent;H=D.parents[3]/'head-redesign-20261008';source=H/'curved-head/openrb-curved-layout-world.stl';m=trimesh.load_mesh(source);f=m.faces
rv=f[:,[0,1,2]].ravel();cv=f[:,[1,2,0]].ravel();graph=coo_matrix((np.ones(len(rv),np.int8),(rv,cv)),shape=(len(m.vertices),len(m.vertices))).tocsr();count,labels=connected_components(graph,directed=False);fl=labels[f[:,0]];del graph,rv,cv
selected=[25,26,27,28]+list(range(91,105));out=D/'actual-pin-components';out.mkdir(exist_ok=True);records=[]
for i in selected:
 q=m.submesh([np.where(fl==i)[0]],append=True);assert q.is_volume,(i,q.is_watertight);p=out/f'pin-component-{i}.stl';q.export(p);records.append({'index':i,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'boundsMm':q.bounds.tolist(),'validVolume':bool(q.is_volume),'faces':len(q.faces)})
report={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sourceConnectedComponents':count,'records':records,'noShapeChanges':True};p=D/'actual-pin-components.json';p.write_text(json.dumps(report,indent=2)+'\n');print({'count':len(records),'sourceComponents':count})
