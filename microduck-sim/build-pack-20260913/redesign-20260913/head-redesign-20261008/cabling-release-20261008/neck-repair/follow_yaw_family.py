"""Single continuous unit-tangent integration; no shortest-rotation branch."""
import math,json,hashlib
from pathlib import Path
from prepare_single_candidate import moved,add,sub,mul,dot,norm
from single_circle_candidate import arc,line
D=Path(__file__).resolve().parent;H=D.parent.parent
A=[-47.,45.2,135.];B=[0.,-25.,44.];U=[-2**-.5,-2**-.5,0.];PREFIX=60.;TURN=135.;RESERVE=8.;R=16.
def tangent(u,q):
 turn=TURN+q.get("head_yaw",0)/2;a=math.radians(turn*u);beta=math.radians(20)*math.sin(math.pi*u);v=[-math.sin(a)*math.cos(beta),math.cos(a)*math.cos(beta),math.sin(beta)]
 return moved(v,{k:deg*(1-u) for k,deg in q.items()},True)
def prefix(q):
 # Composite Simpson integration. The integrand is a unit vector; analytic arclength is exactly PREFIX.
 n=240;pts=[moved(A,q)]
 for i in range(n):
  a=i/n;b=(i+1)/n;ta,tm,tb=tangent(a,q),tangent((a+b)/2,q),tangent(b,q)
  pts.append(add(pts[-1],[(b-a)*PREFIX*(ta[k]+4*tm[k]+tb[k])/6 for k in range(3)]))
 yaw=q.get('head_yaw',0);turn=TURN+yaw/2;roll=abs(q.get('head_roll',0));co=math.cos(math.radians(roll)) if turn*yaw>=0 else 1
 aligned=math.sqrt(max(0,turn*turn+yaw*yaw-2*turn*yaw*co));angular_bound=abs(q.get('neck_pitch',0))+abs(q.get('head_pitch',0))+roll+aligned
 bound=PREFIX/(math.radians(angular_bound)+math.radians(20)*math.pi)
 return pts,bound

def yaw_axis(q):
 a=math.radians(q.get('head_yaw',0)/2);return [math.cos(a)*U[0]-math.sin(a)*U[1],math.sin(a)*U[0]+math.cos(a)*U[1],0.]

def terms(q,B_=None):
 B_=B if B_ is None else B_;u=yaw_axis(q);bp,bl=arc(B_,U,u,R);target=bp[-1];p,rb=prefix(q);c=p[-1];delta=sub(target,c);dy=dot(delta,u);trans=sub(delta,mul(u,dy));d=norm(trans);rr=min(R,d/2)
 return p,rb,c,trans,d,rr,PREFIX+bl+d+(math.pi-2)*rr+abs(dy)+2*RESERVE,bp,bl,u

def path(q,L,B_=None):
 B_=B if B_ is None else B_;p,rb,c,trans,d,rr,need,bp,bl,u=terms(q,B_)
 if d<1e-10:return None
 target=bp[-1];e=mul(trans,1/d);dy=dot(sub(target,c),u);across=d-2*rr;left=(L-PREFIX-bl-across-math.pi*rr+dy)/2;right=left-dy
 if min(left,right)<RESERVE-1e-7:return None
 pts=p[:];top=add(c,mul(u,left));pts+=line(c,top)[1:];pp,l1=arc(top,u,e,rr);pts+=pp[1:];end=add(pp[-1],mul(e,across));pts+=line(pp[-1],end)[1:];pp,l2=arc(end,e,mul(u,-1),rr);pts+=pp[1:];pts+=line(pp[-1],target)[1:];pts+=list(reversed(bp))[1:]
 return {'points':pts,'minimumCenterRadiusMm':min(rb,rr,R),'prefixCurvatureRadiusLowerBoundMm':rb,'coreRadiusMm':rr,'analyticLengthMm':PREFIX+bl+left+right+across+l1+l2,'bodyTangentTransitionLengthMm':bl,'bowAxis':u,'prefixIntegratedLengthMm':PREFIX,'numericalChordLengthMm':sum(math.dist(a,b) for a,b in zip(pts,pts[1:])),'receivingBounds':[[min(v[k] for v in pts)-3.5 for k in range(3)],[max(v[k] for v in pts)+3.5 for k in range(3)]]}

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
 src=H/'usb-access/usb-repair/rigid-domain.json';b=json.loads(src.read_text());ts=[terms(r['jointDegrees']) for r in b['samples']];clear=[i for i,r in enumerate(b['samples']) if not r['nativeShellOriginalBottomIntersectionsMm3']];L=5*math.ceil(max(ts[i][6] for i in clear)/5)
 rows=[{'pose':i,'nativeBlocked':i not in clear,'minimumRequiredFreeLengthMm':t[6],'prefixRadiusBoundMm':t[1],'coreRadiusMm':t[5]} for i,t in enumerate(ts)]
 tests=[]
 for a in [-45.,0.,135.]:
  aa=path({'head_yaw':a-.001},L);bb=path({'head_yaw':a+.001},L);ma,mb=material_points(aa),material_points(bb)
  tests.append({'centerHeadYawDeg':a,'incrementDeg':.002,'maxMaterialPointDisplacementMm':max(math.dist(x,y) for x,y in zip(ma,mb)),'prefixEndpointDisplacementMm':math.dist(terms({'head_yaw':a-.001})[2],terms({'head_yaw':a+.001})[2]),'resamplingChordLengthErrorMm':max(abs(g['analyticLengthMm']-g['numericalChordLengthMm']) for g in [aa,bb])})
 neutral=path({},L);neutral.pop('points');r={'accepted':False,'CADRun':False,'family':'Unit tangent t(u)=FK_rotation(q*(1-u)) Rz((135+yaw/2)u) tiltedY(beta=20deg*sin(pi*u)); integrate over fixed60mm. Joint angles remain explicit, not converted to shortest orientation. Endpoint0 tangent is actual head +Y; endpoint1 follows half of explicit yaw; body R16 transition restores fixed torso tangent. Then existing tangent-continuous two-quarter-circle U; constanttotalfree length by straight legs.','selectedFreeLengthMm':L,'minimumNativeClearRadiusMm':min(min(ts[i][1],ts[i][5]) for i in clear),'nativeClearRadiusFailures':[rows[i] for i in clear if min(ts[i][1],ts[i][5])<9],'neutral':neutral,'antiparallelRegression':tests,'numericalMethod':'240 subinterval compositeSimpson unit-tangent integration, step<=0.25mm; radius lower bound60/(other angular speeds+combined yaw/turn angular-speed upper bound+20deg*pi), from angular-velocity triangle inequality. Fixed material-coordinate sampling discloses chord approximation error.','remaining':'Full229 self, obstacle collisions, angular paths at fixed material coordinates and current head fanout/portal. Bow axis follows half-yaw to keep pose158 return straight away from motor14; torso-end<=85deg R16 arc preserves fixed body connector tangent. This is not whole mechanical acceptance.','rows':rows,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,Path(__file__),D/'prepare_single_candidate.py',D/'single_circle_candidate.py']}}
 (D/'follow-yaw-preparation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['rows','sourceHashes']},indent=2))
if __name__=='__main__':main()
