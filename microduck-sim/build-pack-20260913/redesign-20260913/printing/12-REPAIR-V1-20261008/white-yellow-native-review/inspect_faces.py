from pathlib import Path
import os,json
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh
D=Path(__file__).resolve().parent;P=D.parent;R=P.parent.parent
ori=json.loads((P/'orientation-preparation.json').read_text());out={}
for col in ['White','Yellow']:
 o=next(q for q in ori['parts'] if q['color']==col);m=trimesh.load(R/o['source'],force='mesh');T=np.array(o['printTransform']);pm=m.copy();pm.apply_transform(T)
 rows=[]
 for fi in np.argsort(m.facets_area)[::-1][:30]:
  ids=m.facets[fi];normal=m.facets_normal[fi];area=m.facets_area[fi];n=T[:3,:3]@normal;center=m.triangles_center[ids[0]];offsets=(m.vertices-center)@normal
  rows.append({'facetId':int(fi),'area':float(area),'normalWorld':normal.tolist(),'normalPrint':n.tolist(),'pointWorld':center.tolist(),'planeProtrusionWorldMm':float(offsets.max()),'facetPrintZrange':(float(pm.triangles[ids,:,2].min()),float(pm.triangles[ids,:,2].max()))})
 out[col]={'rows':rows,'boundsCurrentPrint':pm.bounds.tolist()}
(D/'planar-faces.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
