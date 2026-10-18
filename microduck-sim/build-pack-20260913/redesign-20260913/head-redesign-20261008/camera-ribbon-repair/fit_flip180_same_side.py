"""Fixed optical center, flipped CSI port, same-sided cable contacts both toward PCB."""
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from pathlib import Path
import ast,json,math
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import developable_x225_dogleg as dr
D=Path(__file__).resolve().parent;O=D/'positive-x225';cam=np.array([75.63,-9.553380023950195,131.1145988411133]);dr.target=cam+[0,5,0];dr.want=np.column_stack([[0,1,0],[0,0,1],[1,0,0]])
text=(D/'developable_ribbon_inner_entry.py').read_text();node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef) and x.name=='family');node.body[0]=ast.parse('L1,L2,extra,a1,a2,a3,a4,p1,p2,p3,p4=x').body[0];node.body[1]=ast.parse("ops=[('S',8.4+8*abs(math.tan(p1))),('B',a1,p1,-1),('S',L1),('B',a2,p2,-1),('S',L2),('B',a3,p3,1),('S',.3+8*(abs(math.tan(p3))+abs(math.tan(p4)))),('B',a4,p4,-1),('S',9+extra+8*abs(math.tan(p4)))]").body[0];ast.fix_missing_locations(node);exec(compile(ast.Module(body=[node],type_ignores=[]),'<flip same sided>','exec'),dr.__dict__)
lo=[.2,.2,0,2.4,2.4,.1,.1,-.4,-.4,-.6,-.6];hi=[90,60,15,3.6,3.6,1.7,1.7,.4,.4,.6,.6];rows=[]
for total in [73.,100.,150.]:
 def residual(x):
  p,t,w,L,b,_=dr.family(x);rot=Rotation.from_matrix(dr.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;gaps=[z['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(z['phi']))) for a,z in zip(b,b[1:])]
  return np.r_[p-dr.target,rot,L-total,np.minimum(np.array(gaps)-.3,0)*10]
 fit=least_squares(residual,[45,3,1,math.pi,math.pi,1,1,.05,.05,.05,.05],bounds=(lo,hi),max_nfev=500,ftol=1e-12,xtol=1e-12,gtol=1e-12)
 p,t,w,L,b,pr=dr.family(fit.x);rows.append({'lengthTargetMm':total,'parameters':fit.x.tolist(),'maxResidual':max(abs(residual(fit.x))),'materialLengthMm':L,'endPointMm':p.tolist(),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in z.items()} for z in pr]})
(O/'flip180-same-side-fits.json').write_text(json.dumps({'integrationReady':False,'cameraMouth':cam.tolist(),'contactNormal':'+X both board-side; same-sided cable assumed; supports B0210 based on cited manufacturer product','candidates':rows},indent=2)+'\n');print(json.dumps([{k:v for k,v in q.items() if k!='primitives'} for q in rows],indent=2))
