"""One explicit four-U, separated-strand150mm topology at flipped camera port."""
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from pathlib import Path
import json,math,ast
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import developable_x225_dogleg as dr
D=Path(__file__).resolve().parent;O=D/'positive-x225';cam=np.array([75.63,-9.553380023950195,131.1145988411133]);dr.target=cam+[0,5,0];dr.want=np.column_stack([[0,1,0],[0,0,1],[1,0,0]])
def family(x):
 L1,L2,L3,L4,extra,aa,ab,p1,p2,p3,p4,p5,p6=x
 ops=[('S',8.4+8*abs(math.tan(p1))),('B',math.pi,p1,-1,3),('S',L1),('B',math.pi,p2,1,3),('S',L2),('B',math.pi,p3,1,3.6),('S',L3),('B',math.pi,p4,-1,3),('S',L4),('B',aa,p5,1,3),('S',.3+8*(abs(math.tan(p5))+abs(math.tan(p6)))),('B',ab,p6,-1,3),('S',9+extra+8*abs(math.tan(p6)))]
 p,t,w=[a.copy() for a in dr.initial];s=0.;bends=[];primitives=[]
 for op in ops:
  if op[0]=='S':
   L=op[1];primitives.append({'kind':'straight','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy()});p=p+t*L;s+=L
  else:
   ang,phi,sign,R=op[1:];n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=R*ang/math.cos(phi);b={'kind':'cylindrical','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n,'e':e,'q':q,'angle':ang,'phi':phi,'sign':sign,'R':R};bends.append(b);primitives.append(b);p=p+e*(R*ang*math.tan(phi))+q*(R*math.sin(ang))+n*(sign*R*(1-math.cos(ang)));qp=q*math.cos(ang)+n*(sign*math.sin(ang));t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);s+=L
 return p,t,w,s,bends,primitives
dr.family=family
# Per-bend radius in material map, retaining exact isometric surface.
src=(D/'developable_ribbon_inner_entry.py').read_text();node=next(x for x in ast.parse(src).body if isinstance(x,ast.FunctionDef) and x.name=='material_map');node.body[0].body.insert(0,ast.parse("R=b['R']").body[0]);ast.fix_missing_locations(node);exec(compile(ast.Module(body=[node],type_ignores=[]),'<variable bounded radius>','exec'),dr.__dict__)
lo=[25,.2,20,10,0,.2,.2,-.03,-.15,-.15,-.15,-.4,-.4];hi=[50,4,55,25,5,1.3,1.3,.03,.15,.15,.15,.4,.4]
def residual(x):
 p,t,w,L,b,_=family(x);rot=Rotation.from_matrix(dr.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;gaps=[z['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(z['phi']))) for a,z in zip(b,b[1:])];return np.r_[p-dr.target,rot,L-150,np.minimum(np.array(gaps)-.3,0)*10,10*(x[8]-x[9]), max(0,b[3]['p'][1]+36.8)*10]
fit=least_squares(residual,[36,1.8,37,16,1,.7,.7,0,.03,.03,.02,.01,.01],bounds=(lo,hi),max_nfev=400,ftol=1e-12,xtol=1e-12,gtol=1e-12);p,t,w,L,b,pr=family(fit.x);r={'integrationReady':False,'parameters':fit.x.tolist(),'maxResidual':float(max(abs(residual(fit.x)))),'materialLengthMm':L,'endpointMm':p.tolist(),'tangent':t.tolist(),'width':w.tolist(),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in q.items()} for q in pr]};(O/'flip150-edge-fit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='primitives'},indent=2))
