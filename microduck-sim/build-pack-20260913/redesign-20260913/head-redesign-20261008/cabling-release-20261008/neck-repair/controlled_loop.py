"""Test finite smooth service-loop families; no published scene mutation."""
exec(open(__file__.replace('controlled_loop.py','probe_exit.py')).read().split('head=np.array')[0])
from scipy.optimize import brentq
from scipy.special import comb
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['arc','tube']:exec(compile(ast.Module(body=[node],type_ignores=[]),'<geometry>','exec'))
ptail=np.array([1e9]*3);A=np.array([-31.,23.2,125]);exitP,exitL=arc(A,np.array([-1.,0,0]),np.array([0.,1,0]),11.);exitP=np.vstack([exitP,exitP[-1]+[0,25,0]])
b=np.array([-66.,23.2,35]);tb=np.array([0.,1,0]);ts=np.linspace(0,1,401)[:,None]
def bez(control,t=ts):
 n=len(control)-1;return sum(comb(n,i)*(1-t)**(n-i)*t**i*p for i,p in enumerate(control))
def make(a,ta,L,l,u):
 def gen(h,full=False):
  p=np.array([a,a+ta*l,a+ta*l+u*h,b+tb*l+u*h,b+tb*l,b]);pts=bez(p);length=np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()
  if not full:return length-L
  d=bez(5*np.diff(p,axis=0));dd=bez(20*np.diff(p,n=2,axis=0));k=np.linalg.norm(np.cross(d,dd),axis=1)/np.maximum(np.linalg.norm(d,axis=1)**3,1e-14);return pts,float(length),float(1/max(k))
 try:h=brentq(gen,0,1000)
 except ValueError:return None
 return (*gen(h,True),h)
rows=[];L=float(sys.argv[1]) if len(sys.argv)>1 else 320.
for i,q in enumerate(cases):
 poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});Ts={k:poses[k]@inv[k] for k in poses};T=Ts['jaw_soft'];a=(T@np.r_[exitP[-1],1])[:3];ta=T[:3,:3]@[0.,1,0];oo={k:o.transform(Ts[body[k]][:3]) for k,o in obs.items()};best=None
 for l in [25.,40.,60.,80.]:
  for u in [[-1,0,0],[-1,0,.5],[-1,0,1],[-1,1,0],[-1,-1,0]]:
   u=np.array(u,float);u/=np.linalg.norm(u);m=make(a,ta,L,l,u)
   if m is None:continue
   p,length,rad,h=m
   if rad<9:continue
   solid=man(tube(p,7));hh={}
   for k,o in oo.items():
    v=hits(solid,o)
    if v>1e-4:hh[k]=v
   # Score true intersection volume first; retain all failures quantitatively.
   score=(sum(hh.values()),-rad)
   if best is None or score<best[0]:best=(score,{'l':l,'bowDirection':u.tolist(),'bowHeight':h,'radius':rad,'length':length,'hits':hh},p)
   if not hh:break
  if best and not best[1]['hits']:break
 row={'case':i,'q':q,'rigidBlocked':bool(rigid['samples'][i]['rigidIntersectionsMm3']),'candidate':best[1] if best else None};rows.append(row)
 if i%20==0:print(i,L,'bad',sum(x['candidate'] is None or bool(x['candidate']['hits']) for x in rows),'validBad',sum(not x['rigidBlocked'] and (x['candidate'] is None or bool(x['candidate']['hits'])) for x in rows),flush=True)
 if best and all(abs(v)<1e-6 for v in q.values()):tube(best[2],7).export(N/f'controlled-loop-{int(L)}-neutral-world.stl')
(N/f'controlled-loop-{int(L)}.json').write_text(json.dumps({'rows':rows,'L':L,'sourceHashes':hashes,'accepted':False,'scope':'Finite per-pose route feasibility only; changing family parameters between poses is not a motion acceptance.'},indent=2)+'\n')
