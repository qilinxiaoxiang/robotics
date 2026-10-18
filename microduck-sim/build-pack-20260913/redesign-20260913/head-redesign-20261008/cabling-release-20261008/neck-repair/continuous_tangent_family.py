"""Single continuous unit-tangent integration; no shortest-rotation branch."""
import math,json,hashlib
from pathlib import Path
from prepare_single_candidate import moved,add,sub,mul,dot,norm
from single_circle_candidate import arc,line
D=Path(__file__).resolve().parent;H=D.parent.parent
A=[-47.,45.2,135.];B=[0.,-25.,44.];U=[-2**-.5,-2**-.5,0.];PREFIX=55.;TURN=135.;RESERVE=8.;R=16.
def tangent(u,q):
 a=math.radians(TURN*u);v=[-math.sin(a),math.cos(a),0.]
 return moved(v,{k:deg*(1-u) for k,deg in q.items()},True)
def prefix(q):
 # Composite Simpson integration. The integrand is a unit vector; analytic arclength is exactly PREFIX.
 n=220;pts=[moved(A,q)]
 for i in range(n):
  a=i/n;b=(i+1)/n;ta,tm,tb=tangent(a,q),tangent((a+b)/2,q),tangent(b,q)
  pts.append(add(pts[-1],[(b-a)*PREFIX*(ta[k]+4*tm[k]+tb[k])/6 for k in range(3)]))
 bound=PREFIX/math.radians(TURN+sum(abs(v) for v in q.values()))
 return pts,bound

def terms(q,B_=None):
 B_=B if B_ is None else B_;p,rb=prefix(q);c=p[-1];delta=sub(B_,c);dy=dot(delta,U);trans=sub(delta,mul(U,dy));d=norm(trans);rr=min(R,d/2)
 return p,rb,c,trans,d,rr,PREFIX+d+(math.pi-2)*rr+abs(dy)+2*RESERVE

def path(q,L,B_=None):
 B_=B if B_ is None else B_;p,rb,c,trans,d,rr,need=terms(q,B_)
 if d<1e-10:return None
 e=mul(trans,1/d);dy=dot(sub(B_,c),U);across=d-2*rr;left=(L-PREFIX-across-math.pi*rr+dy)/2;right=left-dy
 if min(left,right)<RESERVE-1e-7:return None
 pts=p[:];top=add(c,mul(U,left));pts+=line(c,top)[1:];pp,l1=arc(top,U,e,rr);pts+=pp[1:];end=add(pp[-1],mul(e,across));pts+=line(pp[-1],end)[1:];pp,l2=arc(end,e,mul(U,-1),rr);pts+=pp[1:];pts+=line(pp[-1],B_)[1:]
 return {'points':pts,'minimumCenterRadiusMm':min(rb,rr),'prefixCurvatureRadiusLowerBoundMm':rb,'coreRadiusMm':rr,'analyticLengthMm':PREFIX+left+right+across+l1+l2,'prefixIntegratedLengthMm':PREFIX,'numericalChordLengthMm':sum(math.dist(a,b) for a,b in zip(pts,pts[1:])),'receivingBounds':[[min(v[k] for v in pts)-3.5 for k in range(3)],[max(v[k] for v in pts)+3.5 for k in range(3)]]}

def material_points(g,n=501):
 # Stable material coordinates from0..L; chord resampling error disclosed separately.
 ps=g['points'];ss=[0.]
 for a,b in zip(ps,ps[1:]):ss.append(ss[-1]+math.dist(a,b))
 out=[];i=0
 for j in range(n):
  s=ss[-1]*j/(n-1)
  while i+1<len(ss)-1 and ss[i+1]<s:i+=1
  t=(s-ss[i])/(ss[i+1]-ss[i]) if ss[i+1]>ss[i] else 0
  out.append(add(ps[i],mul(sub(ps[i+1],ps[i]),t)))
 return out

def main():
 src=H/'usb-access/usb-repair/rigid-domain.json';b=json.loads(src.read_text());ts=[terms(r['jointDegrees']) for r in b['samples']];clear=[i for i,r in enumerate(b['samples']) if not r['nativeShellOriginalBottomIntersectionsMm3']];L=5*math.ceil(max(ts[i][-1] for i in clear)/5)
 rows=[{'pose':i,'nativeBlocked':i not in clear,'minimumRequiredFreeLengthMm':t[-1],'prefixRadiusBoundMm':t[1],'coreRadiusMm':t[-2]} for i,t in enumerate(ts)]
 tests=[]
 for a in [-45.,0.,135.]:
  aa=path({'head_yaw':a-.001},L);bb=path({'head_yaw':a+.001},L);ma,mb=material_points(aa),material_points(bb)
  tests.append({'centerHeadYawDeg':a,'incrementDeg':.002,'maxMaterialPointDisplacementMm':max(math.dist(x,y) for x,y in zip(ma,mb)),'prefixEndpointDisplacementMm':math.dist(terms({'head_yaw':a-.001})[2],terms({'head_yaw':a+.001})[2]),'resamplingChordLengthErrorMm':max(abs(g['analyticLengthMm']-g['numericalChordLengthMm']) for g in [aa,bb])})
 neutral=path({},L);neutral.pop('points');r={'accepted':False,'CADRun':False,'family':'Unit tangent t(u)=FK_rotation(q*(1-u)) Rz(135u) Y; integrate over fixed55mm. Joint angles remain explicit, not converted to shortest orientation. Endpoint0 tangent is actual head +Y; endpoint1 is fixed rear-left U. Then existing tangent-continuous two-quarter-circle U; constanttotalfree length by straight legs.','selectedFreeLengthMm':L,'minimumNativeClearRadiusMm':min(min(ts[i][1],ts[i][-2]) for i in clear),'nativeClearRadiusFailures':[rows[i] for i in clear if min(ts[i][1],ts[i][-2])<9],'neutral':neutral,'antiparallelRegression':tests,'numericalMethod':'220 subinterval compositeSimpson unit-tangent integration, step<=0.25mm; radius lower bound55/(135deg+sum absolute joint angles in radians), from angular-velocity triangle inequality. Fixed material-coordinate sampling discloses chord approximation error.','remaining':'Full229 self, obstacle collisions, angular paths at fixed material coordinates and current head fanout/portal. This fixes the known algebraic branch, not whole mechanical acceptance.','rows':rows,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,Path(__file__),D/'prepare_single_candidate.py',D/'single_circle_candidate.py']}}
 (D/'continuous-tangent-preparation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['rows','sourceHashes']},indent=2))
if __name__=='__main__':main()
