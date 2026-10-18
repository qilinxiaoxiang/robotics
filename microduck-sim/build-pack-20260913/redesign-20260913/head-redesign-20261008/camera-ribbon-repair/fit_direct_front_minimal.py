"""Finite three-cylinder fixed-end connection; length is free or73mm, not forced200."""
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from pathlib import Path
import ast,json,math
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import developable_x225_dogleg as dr
D=Path(__file__).resolve().parent;O=D/'positive-x225'
text=(D/'developable_ribbon_inner_entry.py').read_text();node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef) and x.name=='family')
node.body[0]=ast.parse('L1,L2,extra,a1,a2,a3,p2,p3,p1=x').body[0]
node.body[1]=ast.parse("ops=[('S',8.4+8*abs(math.tan(p1))),('B',a1,p1,1),('S',L1),('B',a2,p2,1),('S',L2),('B',a3,p3,-1),('S',9+extra+8*abs(math.tan(p3)))]").body[0];ast.fix_missing_locations(node);exec(compile(ast.Module(body=[node],type_ignores=[]),'<short family>','exec'),dr.__dict__)
lo=[.2,.2,0.,2.9,.1,.1,-.5,-.5,-.15];hi=[30.,10.,5.,3.3,1.6,1.6,.5,.5,.15]
rows=[]
for total in [0.,50.,73.]:
 for a1 in [math.pi]:
  def residual(x):
   p,t,w,L,b,_=dr.family(x);rot=Rotation.from_matrix(dr.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30
   gaps=[z['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(z['phi']))) for a,z in zip(b,b[1:])]
   return np.r_[p-dr.target,rot,((L-total) if total else L*.005),np.minimum(np.array(gaps)-.3,0)*10]
  fit=least_squares(residual,[10,1,1,a1,1,1,.03,.03,.05],bounds=(lo,hi),max_nfev=350,ftol=1e-11,xtol=1e-11,gtol=1e-11)
  p,t,w,L,b,_=dr.family(fit.x);endpoint=np.r_[p-dr.target,Rotation.from_matrix(dr.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30];gaps=[z['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(z['phi']))) for a,z in zip(b,b[1:])]
  rows.append({'targetLengthMm':total or None,'parameters':fit.x.tolist(),'materialLengthMm':L,'endpointOrientationResidual':max(abs(endpoint)),'minimumFlatGapMm':min(gaps),'endpointMm':p.tolist(),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in q.items()} for q in dr.family(fit.x)[5]]})
r={'integrationReady':False,'scope':'Six finite numerical endpoint fits; no physical acceptance','candidates':rows};(O/'direct-front-minimal-fits.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([{k:v for k,v in q.items() if k!='primitives'} for q in rows],indent=2))
