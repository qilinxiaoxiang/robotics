from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,numpy as np,trimesh
D=Path(__file__).resolve().parent;R=D.parent.parent;P=R/'printing/11-ASSEMBLY-REPAIR-20261008';N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
ori=json.loads((P/'orientation-preparation.json').read_text());rows=[]
for color,name,member,tz in [('yellow','jaw_frame','object_1.model',14.782238),('yellow','jaw_passive_cheek','object_2.model',8.76256371),('white','lower_pad','object_1.model',4.29685879)]:
 row=next(q for q in ori['parts'] if q['key']==name);T=np.array(row['printTransform']);T[:2,3]+=row['placementXYMm']
 with zipfile.ZipFile(P/f'{color}-preflight/{color.title()}_preflight.3mf') as z:root=E.fromstring(z.read('3D/Objects/'+member))
 verts=np.array([[float(v.get(k)) for k in ['x','y','z']] for v in root.iter(N+'vertex')]);verts+=np.array([*row['placementXYMm'],tz]);faces=np.array([[int(f.get(k)) for k in ['v1','v2','v3']] for f in root.iter(N+'triangle')]);m=trimesh.Trimesh(verts,faces,process=True);m.apply_transform(np.linalg.inv(T));sections=[]
 for y in ([-45,-43,-41,-39,-37,-35,-34,-33,-32,-31] if 'cheek' in name else [38,39,40,41,42,43,44] if name=='jaw_frame' else [-40,-35,-30,-25]):
  sec=m.section(plane_origin=[0,y,0],plane_normal=[0,1,0]);curves=[]
  if sec:
   for q in sec.discrete:
    rr=np.linalg.norm(q[:,[0,2]]-[26.1,118.6146],axis=1)
    curves.append({'bounds':np.array([q.min(0),q.max(0)]).tolist(),'radiusRangeAboutPivot':[float(rr.min()),float(rr.max())]})
  sections.append({'worldY':y,'curves':curves})
 rows.append({'part':name,'watertight':m.is_watertight,'boundsWorld':m.bounds.tolist(),'bearingAxisPrint':T[:3,1].tolist(),'bearingAxisTiltDegreesFromZ':float(np.degrees(np.arccos(abs(T[2,1])))),'sections':sections})
(D/'jaw-native-geometry-sections.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
