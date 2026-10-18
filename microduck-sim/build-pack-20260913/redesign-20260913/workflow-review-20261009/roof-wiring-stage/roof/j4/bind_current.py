import os,json,hashlib,gc
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;R=D.parents[3];M=R/'workflow-review-20261009/original-body-converter/fusion-import-manifest.json';r=next(x for x in json.loads(M.read_text())['parts']if x['key']=='openrb');s=json.loads((D/'extraction.json').read_text());rows=[]
for path in [s['source'],r['file']]:
 p=Path(path);m=tm.load(p,force='mesh');v=m.vertices.astype(np.float32);v=v[np.lexsort((v[:,2],v[:,1],v[:,0]))];rows.append({'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'vertices':len(v),'uniqueVertexFloat32Sha256':hashlib.sha256(v.tobytes()).hexdigest(),'triangles':len(m.faces)});del m,v;gc.collect()
assert rows[0]['uniqueVertexFloat32Sha256']==rows[1]['uniqueVertexFloat32Sha256'] and rows[0]['triangles']==rows[1]['triangles'];assert r['importTranslationMm']==[0,0,0]
(D/'current-mesh-binding.json').write_text(json.dumps({'passed':True,'manifest':str(M),'manifestSha256':hashlib.sha256(M.read_bytes()).hexdigest(),'rows':rows,'scope':'Exact unique float32 vertex set and triangle count; existing source provenance supplies topology. Current part transform is zero.'},indent=2)+'\n');print('Current OpenRB vertices match source')
