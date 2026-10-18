from pathlib import Path
import os,sys,json,math,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares
D=Path(__file__).resolve().parent;H=D.parents[1];C=H/'camera-ribbon-repair';Q=C/'fixed-pose-local-bend';sys.path.insert(0,str(C));import fit_spacer2_tilted_complete as base
source=Q/'spacer2-tilted-complete-fit.json';old=np.array(json.loads(source.read_text())['parameters']);normal=-base.T[:3,0]
def point(x,s):
 p,t,w,L,bends,pr=base.family(x)
 for b in bends:
  ds=s-b['s0'];phi=b['phi'];bc=ds*math.cos(phi);ac=ds*math.sin(phi)
  if bc<0:return b['p']+b['t']*ds
  if bc<=b['R']*b['angle']:
   a=bc/b['R'];return b['p']+b['e']*ac+b['q']*b['R']*math.sin(a)+b['n']*(b['sign']*b['R']*(1-math.cos(a)))
 return p+t*(s-L)
ids=[2,3,4,5,6,7,9,10,11,12,13]
lo=old[ids]-np.array([2,2,2,4,0,0,.10,.10,.12,.12,.08]);hi=old[ids]+np.array([2,2,2,4,2,5,.10,.10,.12,.12,.08]);lo[4]=1;lo[5]=4;hi[4]=3
rows=[]
for lift in [.5,.9]:
 def unpack(z):x=old.copy();x[ids]=z;return x
 def residual(z):
  x=unpack(z);p,t,w,L,b,pr=base.family(x);flat=x[7]-5.75*abs(math.tan(x[12]));local=[]
  for s in [181,185,189]:local.extend((point(x,s)-point(old,s)-normal*lift))
  return np.r_[base.residual(x)*300,local,np.minimum(flat-6.4,0)*12,(z-old[ids])*.002]
 fit=least_squares(residual,old[ids],bounds=(lo,hi),max_nfev=400,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 x=unpack(fit.x);p,t,w,L,b,pr=base.family(x);r={'accepted':False,'requestedLocalLiftMm':lift,'parameters':x.tolist(),'evaluations':fit.nfev,'maxConstraintResidual':float(max(abs(base.residual(x)))),'materialLengthMm':float(L),'endpointResidualMm':float(np.linalg.norm(p-base.target)),'fullWidthFlatMm':float(x[7]-5.75*abs(math.tan(x[12]))),'assumedInsertionMm':4.4,'outsideFlatMm':float(x[7]-5.75*abs(math.tan(x[12]))-4.4),'liftSamples':[{'s':s,'normalLiftMm':float((point(x,s)-point(old,s))@normal),'deltaMm':(point(x,s)-point(old,s)).tolist()}for s in [181,185,189]],'sourceHashes':{str(v):hashlib.sha256(v.read_bytes()).hexdigest()for v in [source,C/'fit_spacer2_tilted_complete.py',Q/'pi-spacer2-pose.json',Path(__file__)]}}
 (D/('fit-lift-'+str(lift)+'.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append(r);print(json.dumps(r),flush=True)
