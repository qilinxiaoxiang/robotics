import json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import bounded_amp_check as c
D=Path(__file__).resolve().parent;H=D.parent;R=H.parent;P=R/'printing/11-ASSEMBLY-REPAIR-20261008';f=P/'black-preflight/Black_preflight.3mf';z=zipfile.ZipFile(f);ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'};r=ET.fromstring(z.read('3D/Objects/neck_pitch_1.model'));v=[[float(a.get(k)) for k in ['x','y','z']] for a in r.findall('.//m:vertex',ns)];faces=[[int(a.get(k)) for k in ['v1','v2','v3']] for a in r.findall('.//m:triangle',ns)];c.guarded_import();verts=c.np.array(v)+[128,128,13.8470001];mesh=c.tm.Trimesh(verts,faces,process=True);rows=[]
for zz in [.0001,.2,.4,1,1.8,2,2.8,3.8,4.0,18.6935]:
 s=mesh.section(plane_origin=[128,128,zz],plane_normal=[0,0,1]);curves=s.discrete if s else [];rows.append({'z':zz,'curves':[{'points':len(p),'bounds':c.np.array([p.min(0),p.max(0)]).tolist(),'radiusAboutCenterRange':c.np.linalg.norm(p[:,:2]-[128,128],axis=1).min().item(),'maxRadius':c.np.linalg.norm(p[:,:2]-[128,128],axis=1).max().item()} for p in curves]})
out={'watertight':mesh.is_watertight,'bounds':mesh.bounds.tolist(),'sections':rows};(D/'black-geometry-sections.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
