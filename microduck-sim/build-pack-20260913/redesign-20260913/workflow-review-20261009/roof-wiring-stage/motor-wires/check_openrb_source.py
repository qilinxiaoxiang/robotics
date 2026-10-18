from pathlib import Path
import json,hashlib
import numpy as np,trimesh
D=Path(__file__).resolve().parent;a=json.loads((D/'obstacles/openrb.json').read_text());b=json.loads((D/'openrb-port-probe.json').read_text())
def canonical(path):
 m=trimesh.load_mesh(path,process=False);t=np.asarray(m.triangles,dtype='<f4');v=t.view([('x','<f4'),('y','<f4'),('z','<f4')]).reshape(-1,3);v.sort(axis=1,order=['x','y','z']);q=np.ascontiguousarray(v).view('V36').reshape(-1);q.sort();return q
x=canonical(a['file']);y=canonical(b['source']);eq=bool(np.array_equal(x,y));result={'passed':eq,'criterion':'Exact float32 triangle-coordinate multiset equality, including all 317300 source triangles, independent of winding/ordering.','currentFile':a['file'],'currentSha256':hashlib.sha256(Path(a['file']).read_bytes()).hexdigest(),'registeredSourceFile':b['source'],'registeredSourceSha256':hashlib.sha256(Path(b['source']).read_bytes()).hexdigest()};(D/'openrb-current-source-equivalence.json').write_text(json.dumps(result,indent=2));print(result);assert eq
