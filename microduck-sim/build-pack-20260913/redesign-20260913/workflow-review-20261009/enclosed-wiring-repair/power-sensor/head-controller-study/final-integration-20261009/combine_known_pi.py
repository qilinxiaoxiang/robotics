from pathlib import Path
import numpy as np,json
F=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009');r=json.loads((F/'joint-package.json').read_text());old=np.array(r['piCurrentWorldDelta']);p=np.radians(100);P=np.eye(4);P[:3,:3]=[[np.cos(p),0,np.sin(p)],[0,1,0],[-np.sin(p),0,np.cos(p)]];P[:3,3]=np.array([59.2,0,128.7])-P[:3,:3]@np.array([59,-1,131.5])
for q in r['parts']:
 if q['group']in['pi','pi_interface_conditional']:q['worldTransform']=(P@np.linalg.inv(old)@q['worldTransform']).tolist()
r['piCurrentWorldDelta']=P.tolist();r['stage']='Parent-requested single combination of prior clear Pi pose and flipped controller. Pending coupled check; not accepted.';(F/'joint-known-pi-package.json').write_text(json.dumps(r,indent=2)+'\n')
s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'", "src=F/'joint-known-pi-package.json'").replace("'joint-check-'", "'known-pi-check-'");(F/'check_known_pi_package.py').write_text(s)
