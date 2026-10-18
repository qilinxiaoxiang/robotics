from pathlib import Path
import sys,json,numpy as np,trimesh,collections
O=Path(__file__).resolve().parent;A=O.parents[1]/'assembly';S=O.parents[2];ns={'__file__':str(A/'inspect_joint_interfaces.py')};exec((A/'inspect_joint_interfaces.py').read_text().split('rows=[]')[0],ns);circles=ns['circles'];fk=ns['fk'];raw=ns['raw'];out={}
for name in ['face_part','top_head_shell','bottom_head_shell','motor_support','CURRENTcap']:
 if name=='CURRENTcap':m=trimesh.load(O.parent/'head-cap-usb-service-body.stl')
 elif name=='motor_support':m=trimesh.load(A/'mouth-support/motor-support-coaxial-assembly.stl')
 else:
  g=next(g for g in fk()[1] if g['body']=='jaw_soft' and g['mesh']==name);m=raw(name).apply_transform(g['local'])
 groups=collections.defaultdict(list)
 for ax in range(3):
  for v in np.arange(m.bounds[0,ax]+.125,m.bounds[1,ax],.5):
   for c in circles(m,ax,v):
    if .55<c['radius']<3:
     xyz=np.insert(c['center_other_axes'],ax,v);inside=bool(m.contains([xyz])[0]);key=(ax,tuple(round(a,2) for a in c['center_other_axes']),round(c['radius'],2),inside);groups[key].append(float(v))
 out[name]={'bounds':m.bounds.tolist(),'features':[dict(axis=k[0],other_axes_center=k[1],radius=k[2],solid_center=k[3],axial_range=[min(v),max(v)]) for k,v in groups.items()]};print(name,json.dumps(out[name]),flush=True)
(O/'electronics-head-closure-survey-current.json').write_text(json.dumps(out,indent=2))
