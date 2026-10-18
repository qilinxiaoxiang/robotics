from pathlib import Path
import numpy as np,json
out=Path(__file__).resolve().parent;d=np.load('/tmp/microduck-hardware-inspection/mesh-12.npz');t=d['vertices'][d['faces']]
def hits(axis,coord,lo,hi):
 oth=[i for i in range(3) if i!=axis];p=t[:,:,oth];a,b,c=p[:,0],p[:,1],p[:,2]
 den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);good=np.abs(den)>1e-12
 aa=a[good];bb=b[good];cc=c[good];dd=den[good];u=((bb[:,1]-cc[:,1])*(coord[0]-cc[:,0])+(cc[:,0]-bb[:,0])*(coord[1]-cc[:,1]))/dd;v=((cc[:,1]-aa[:,1])*(coord[0]-cc[:,0])+(aa[:,0]-cc[:,0])*(coord[1]-cc[:,1]))/dd;w=1-u-v;vals=u*t[good,0,axis]+v*t[good,1,axis]+w*t[good,2,axis];ok=(u>=-1e-9)&(v>=-1e-9)&(w>=-1e-9)&(vals>=lo)&(vals<=hi)
 return vals[ok]
rows=[]
for y in [-28.499,8.2]:
 stems=[]
 for z in [-18.365,18.365]:
  tests=[hits(0,[y+dy,z+dz],-4.1,3) for dy in np.linspace(-2.4,2.4,17) for dz in np.linspace(-.5,.5,11)]
  stems.append({'z':z,'rays':len(tests),'blocked_rays':sum(len(t)>0 for t in tests)})
 tests=[hits(2,[x,y+dy],-18.865,18.865) for x in np.linspace(-4.1,-3.1,11) for dy in np.linspace(-2.4,2.4,17)]
 rows.append({'y':y,'strap_width':4.8,'strap_thickness':1.0,'stem_x_range':[-4.1,3.0],'return_x_range':[-4.1,-3.1],'stems':stems,'return_rays':len(tests),'return_blocked_rays':sum(len(t)>0 for t in tests)})
(out/'strap-route-check.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
