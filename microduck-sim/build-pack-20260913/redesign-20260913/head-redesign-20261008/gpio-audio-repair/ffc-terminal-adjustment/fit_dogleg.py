from pathlib import Path
import os,sys,json,math,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares
D=Path(__file__).resolve().parent;H=D.parents[1];C=H/'camera-ribbon-repair';Q=C/'fixed-pose-local-bend';sys.path.insert(0,str(C));import fit_spacer2_tilted_complete as base
src=(C/'fit_spacer2_tilted_complete.py').read_text();f=src[src.index('def family('):src.index('def residual(')].replace("('S',E),('B',lastangle", "('S',E),('B',dogAngle,0,-1,1),('S',2.),('B',dogAngle,0,1,1),('S',2.),('B',lastangle")
ns=vars(base).copy();exec(f,ns);family=ns['family'];old=np.array(json.loads((Q/'spacer2-tilted-complete-fit.json').read_text())['parameters']);ids=[2,3,4,5,6,7,9,10,11,12,13];normal=-base.T[:3,0]
def r(x):
 p,t,w,L,b,pr=family(x);rr=base.Rotation.from_matrix(base.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;g=[z['s0']-a['s1']-5.75*abs(math.tan(a['phi']))-5.75*abs(math.tan(z['phi'])) for a,z in zip(b,b[1:])];return np.r_[p-base.target,rr,L-200,np.minimum(np.array(g)-.3,0)*5]
lo=[23,7,10,35,1,7.5,.5,-.85,3,-.3,3.04];hi=[33,16,18,54,3,10,.8,-.6,3.25,.3,3.26]
for angle in [.25,.35]:
 ns['dogAngle']=angle
 def unpack(z):x=old.copy();x[ids]=z;return x
 def fun(z):
  x=unpack(z);flat=x[7]-5.75*abs(math.tan(x[12]));return np.r_[r(x)*100,np.minimum(flat-6.4,0)*20,(z-old[ids])*.001]
 z0=np.clip(old[ids],np.array(lo)+1e-6,np.array(hi)-1e-6);z0[4]=1.5
 fit=least_squares(fun,z0,bounds=(lo,hi),max_nfev=500,ftol=1e-10,xtol=1e-10,gtol=1e-10);x=unpack(fit.x);p,t,w,L,b,pr=family(x);out={'accepted':False,'topology':'two opposite R1 dogleg bends before final U; straight2+2','dogAngle':angle,'parameters':x.tolist(),'maxConstraintResidual':float(max(abs(r(x)))),'materialLengthMm':L,'endpointResidualMm':float(np.linalg.norm(p-base.target)),'fullWidthFlatMm':float(x[7]-5.75*abs(math.tan(x[12]))),'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [C/'fit_spacer2_tilted_complete.py',Q/'spacer2-tilted-complete-fit.json',Path(__file__)]},'primitives':[{k:v.tolist()if isinstance(v,np.ndarray)else v for k,v in a.items()}for a in pr]};(D/f'dogleg-{angle}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['primitives','sourceHashes']}),flush=True)
