from pathlib import Path
import json,base64,sys,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent
plan=json.loads((H/'usb-access/usb-repair/positive-x225-obstacle-plan.json').read_text())['obstacles']
key=sys.argv[1]
a_path=H/'gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'
b_path=Path(plan[key]['source'])
if key in ['jaw_support','jaw_frame','lower_pad']:
 b_path=H/'cabling-release-20261008/neck-repair/original-recovery'/('original-support-world.stl' if key=='jaw_support' else 'original-'+key+'-world.stl')
def solid(p):
 if p.suffix=='.json':
  d=json.loads(p.read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
 else:m=trimesh.load(p,force='mesh')
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
 assert s.status()==mf.Error.NoError,(str(p),s.status())
 return s
cap,other=solid(a_path),solid(b_path);bb=np.array(other.bounding_box()).reshape(2,3)
rows=[]
for z in np.arange(40,-.001,-.25):
 a=cap.translate([0,0,z]);ab=np.array(a.bounding_box()).reshape(2,3)
 if np.any(ab[0]>=bb[1]) or np.any(bb[0]>=ab[1]):v=0
 else:
  inter=a^other;assert inter.status()==mf.Error.NoError;v=max(0,float(inter.volume()))
 rows.append({'offsetZmm':float(z),'volumeMm3':v})
peak=max(rows,key=lambda r:r['volumeMm3']);out={'key':key,'moving':'head_cap','stepMm':.25,'startZmm':40,'rows':rows,'peak':peak,'passed':peak['volumeMm3']<1e-4,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a_path,b_path,Path(__file__)]}}
(D/(key+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['key','peak','passed']}))
