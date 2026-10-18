"""Six finite orientation solves for one two-cylinder transition, no CAD acceptance."""
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from pathlib import Path
import numpy as np,json,math
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;O=D/'positive-x225';a=json.loads((O/'roof-30deg-prefix-full-static.json').read_text());start=np.array(a['endpointMm']);t0=np.array(a['endTangent']);w0=np.array(a['endWidthAxis']);want=np.column_stack([[-1,0,0],[0,-1,0],[0,0,1]])
def bend(p,t,w,ang,phi,sign):
 n=np.cross(t,w);e=w*np.cos(phi)+t*np.sin(phi);q=t*np.cos(phi)-w*np.sin(phi);p=p+e*(3*ang*np.tan(phi))+q*(3*np.sin(ang))+n*(sign*3*(1-np.cos(ang)));qp=q*np.cos(ang)+n*(sign*np.sin(ang));return p,e*np.sin(phi)+qp*np.cos(phi),e*np.cos(phi)-qp*np.sin(phi)
rows=[]
for signs in [(-1,-1),(-1,1),(1,-1),(1,1)]:
 for phi1 in [-math.pi/6,0.,math.pi/6]:
  def calc(x):
   aa,ab,pb=x;p,t,w=bend(start,t0,w0,aa,phi1,signs[0]);flat=8*(abs(np.tan(phi1))+abs(np.tan(pb)))+.5;p+=t*flat;return (*bend(p,t,w,ab,pb,signs[1]),flat)
  def res(x):
   p,t,w,flat=calc(x);return Rotation.from_matrix(want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()
  fit=least_squares(res,[1.5,1.5,.3],bounds=([.02,.02,-1.0],[3.13,3.13,1.0]),max_nfev=120)
  p,t,w,flat=calc(fit.x);rows.append({'signs':signs,'phi1':phi1,'parameters':fit.x.tolist(),'residual':float(np.linalg.norm(res(fit.x))),'flat':flat,'end':p.tolist(),'length':float(3*fit.x[0]/np.cos(phi1)+flat+3*fit.x[1]/np.cos(fit.x[2]))})
(O/'roof-frame-up-transition-fits.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(sorted(rows,key=lambda q:q['residual'])[:5],indent=2))
