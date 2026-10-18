from pathlib import Path
import os,json,math,time,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.optimize import least_squares
import fit_spacer2_monotone as route
D=Path(__file__).parent;Q=D/'fixed-pose-local-bend';field=np.load(Q/'spacer2-field.npz');S,V=np.meshgrid(np.arange(5,195.61,1.5),np.linspace(-.5,.5,9),indexing='ij');S=S.ravel();V=V.ravel()*np.where(S<=35,16,np.where(S<40,16-.9*(S-35),11.5));x0=np.array(json.loads((Q/'spacer2-rev2-monotone-fit.json').read_text())['parameters']);start=time.monotonic();best=[float('inf'),x0]
def points(x):
 p,t,w,L,bs,pr=route.family(x);out=np.zeros((len(S),3));left=np.ones(len(S),bool)
 for b in bs:
  ds=S-b['s0'];ac=ds*math.sin(b['phi'])+V*math.cos(b['phi']);bc=ds*math.cos(b['phi'])-V*math.sin(b['phi']);q=left&(bc<0);out[q]=b['p']+ds[q,None]*b['t']+V[q,None]*b['w'];left[q]=False;q=left&(bc<=b['R']*b['angle']);a=bc[q]/b['R'];out[q]=b['p']+ac[q,None]*b['e']+b['R']*np.sin(a[:,None])*b['q']+b['sign']*b['R']*(1-np.cos(a[:,None]))*b['n'];left[q]=False
 out[left]=p+(S[left]-L)[:,None]*t+V[left,None]*w
 return out
def residual(x):
 pp=points(x);idx=(pp-field['origin'])/float(field['step']);dist=map_coordinates(field['sdf'].astype(np.float64),idx.T,order=1,mode='constant',cval=-5);r=np.r_[route.residual(x)*50,np.maximum(.55-dist,0)*3];score=np.linalg.norm(r)
 if score<best[0]:best[:]=[score,x.copy()]
 if time.monotonic()-start>95:raise TimeoutError()
 return r
lo=[24,8.5,14,8.5,40,1,5,.02,-.90,.65,3.0,-.15,3.02];hi=[40,24,42,32,66,6,15,.12,-.65,.90,3.28,.15,3.26]
try:fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=250,diff_step=1e-5,xtol=1e-8,ftol=1e-8,gtol=1e-8);x=fit.x
except TimeoutError:x=best[1]
p,t,w,L,bs,pr=route.family(x);dist=map_coordinates(field['sdf'].astype(np.float64),((points(x)-field['origin'])/float(field['step'])).T,order=1,mode='constant',cval=-5)
r={'accepted':False,'parameters':x.tolist(),'maxConstraintResidual':float(max(abs(route.residual(x)))),'materialLengthMm':L,'minimumApproxFieldGapMm':float(min(dist)),'sampleCount':len(dist),'underTargetSamples':int(sum(dist<.55)),'elapsedSeconds':time.monotonic()-start,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D/'fit_spacer2_monotone.py',Q/'spacer2-field.npz']}}
(Q/'spacer2-local-field-fit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
