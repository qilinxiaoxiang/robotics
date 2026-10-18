from pathlib import Path
import json,numpy as np
F=Path(__file__).resolve().parent;r=json.loads((F/'original-inset-pi4-package.json').read_text());T0=np.array(r['boardNativeToWorld']);P0=np.array(r['piCurrentWorldDelta']);T=np.eye(4);a=np.radians(10);T[:3,:3]=np.column_stack([[0,1,0],[-np.cos(a),0,-np.sin(a)],[-np.sin(a),0,np.cos(a)]]);T[:3,3]=[40,0,138.5];P=np.eye(4);P[:3,:3]=[[0,1,0],[0,0,-1],[-1,0,0]];P[:3,3]=np.array([45,-18,128.5])-P[:3,:3]@np.array([59,-1,131.5]);assert np.linalg.det(P[:3,:3])>0.999
for q in r['parts']:
 if q['group']=='controller':q['worldTransform']=(T@np.linalg.inv(T0)@q['worldTransform']).tolist()
 elif q['group']in ['pi','pi_interface_conditional']:q['worldTransform']=(P@np.linalg.inv(P0)@q['worldTransform']).tolist()
r['boardNativeToWorld']=T.tolist();r['piCurrentWorldDelta']=P.tolist();r['stage']='One side-wall section-led candidate: complete original OpenRB + received straight C moved forward; Pi GPIO down/out toward negative-Y flank; no printed features removed. Diagnostic for local internal support relief.';(F/'side-wall-package.json').write_text(json.dumps(r,indent=2)+'\n');s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'","src=F/'side-wall-package.json'").replace("'joint-check-'","'side-wall-check-'");(F/'check_side_wall.py').write_text(s)
