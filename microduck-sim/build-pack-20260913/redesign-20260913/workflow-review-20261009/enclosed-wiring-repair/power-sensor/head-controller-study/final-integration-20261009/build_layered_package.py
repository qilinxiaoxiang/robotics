from pathlib import Path
import json,numpy as np,hashlib,trimesh
F=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009');r=json.loads((F/'joint-known-pi-package.json').read_text());P0=np.array(r['piCurrentWorldDelta']);T0=np.array(r['boardNativeToWorld']);p=np.radians(6);Ry=np.array([[np.cos(p),0,-np.sin(p)],[0,1,0],[np.sin(p),0,np.cos(p)]]);P=np.eye(4);P[:3,:3]=Ry@np.array([[0,-1,0],[-1,0,0],[0,0,-1]]);P[:3,3]=np.array([44,-9,148])-P[:3,:3]@np.array([59,-1,131.5]);p=np.radians(10);T=np.eye(4);T[:3,:3]=np.column_stack([[0,1,0],[-np.cos(p),0,-np.sin(p)],[-np.sin(p),0,np.cos(p)]]);T[:3,3]=[40,15,136.5]
for q in r['parts']:
 if q['group'] in ['pi','pi_interface_conditional']:q['worldTransform']=(P@np.linalg.inv(P0)@q['worldTransform']).tolist()
 elif q['group']=='controller':q['worldTransform']=(T@np.linalg.inv(T0)@q['worldTransform']).tolist()
 elif q['group']=='speaker':M=np.array(q['worldTransform']);M[:3,3]+=[5,-2,0];q['worldTransform']=M.tolist()
 elif q['group']=='amp':
  m=trimesh.load_mesh(q['file']);centre=m.bounds.mean(axis=0);V=np.eye(4);V[:3,3]=np.array([65,25,134.7])-centre;q['worldTransform']=V.tolist()
r['piCurrentWorldDelta']=P.tolist();r['boardNativeToWorld']=T.tolist();r['stage']='One section-led layered arrangement: top Pi inverted; original-axis controller front-high follows roof; full plug receivers retained. Not accepted.';r['reason']='C rear shoulder moved forward and down to follow low rear arch; Pi GPIO points down, MicroB points horizontally inward; amp placed beyond motor15 front and behind camera.';(F/'layered-package.json').write_text(json.dumps(r,indent=2)+'\n');s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'","src=F/'layered-package.json'").replace("'joint-check-'","'layered-check-'");(F/'check_layered.py').write_text(s)
