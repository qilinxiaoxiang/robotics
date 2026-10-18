from pathlib import Path
import sys,numpy as np,json
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk,raw
b,gs=fk();mot=[g for g in gs if g['mesh']=='xl330'];rows=[]
for g in gs:
 if not g['mesh'].startswith('seeed_bearing'):continue
 c=(g['world']@np.r_[raw(g['mesh']).bounds.mean(0),1])[:3];cs=[]
 for m in mot:
  p=(np.linalg.inv(m['world'])@np.r_[c,1])[:3];score=np.linalg.norm(p[1:]);cs.append((score,abs(abs(p[0])-14.5),m,p))
 cs.sort(key=lambda t:(t[0]+t[1]));score,ax,m,p=cs[0]
 r={'bearing_body':g['body'],'bearing_index':g['index'],'bearing_mesh':g['mesh'],'motor_body':m['body'],'motor_index':m['index'],'center_in_motor_mm':p.tolist(),'radial_mm':float(score)};rows.append(r);print(r)
(H/'bearing-to-motor.json').write_text(json.dumps(rows,indent=2))
