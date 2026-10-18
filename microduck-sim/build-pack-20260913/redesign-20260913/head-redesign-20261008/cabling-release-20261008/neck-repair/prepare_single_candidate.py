"""Standard-library-only numeric preparation. No CAD imports or clearance claims."""
from pathlib import Path
import math,json,hashlib
D=Path(__file__).resolve().parent;H=D.parent.parent
BASE=H/'usb-access/usb-repair/rigid-domain.json'
rows=json.loads(BASE.read_text())['samples']
def add(a,b):return [a[i]+b[i] for i in range(3)]
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def mul(a,s):return [v*s for v in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):return math.sqrt(dot(a,a))
def rot(v,axis,theta):return add(add(mul(v,math.cos(theta)),mul(cross(axis,v),math.sin(theta))),mul(axis,dot(axis,v)*(1-math.cos(theta))))
# Product of exponentials, neutral-world screw axes from source FK.
JOINTS=[('neck_pitch',[26,14.5,32.4215],[0,-1,0]),('head_pitch',[26,14.5,82.4215],[0,1,0]),('head_yaw',[26,0,101.1146],[0,0,1]),('head_roll',[8.1,0,115.6146],[-1,0,0])]
def moved(p,q,vector=False):
 for name,origin,axis in reversed(JOINTS):
  angle=math.radians(q.get(name,0));p=rot(p,axis,angle) if vector else add(origin,rot(sub(p,origin),axis,angle))
 return p
# R16 outlet + 10mm straight, a strict prefix of previously checked +25mm exit.
A=[-47.,23.2,151.];B=[-66.,50.,35.];TA=[0,0,1.];TB=[0,0,1.]
R_SCREEN=16.;LEAD=6*R_SCREEN;H_MIN=LEAD;BOW=[0.,1,0]
def control(q,h):
 a=moved(A,q);ta=moved(TA,q,True);ap=add(a,mul(ta,LEAD));bp=add(B,mul(TB,LEAD))
 return [a,ap,add(ap,mul(BOW,h)),add(bp,mul(BOW,h)),bp,B]
def bez(p,t):
 n=len(p)-1
 return [sum(math.comb(n,i)*(1-t)**(n-i)*t**i*p[i][j] for i in range(n+1)) for j in range(3)]
def derivatives(p):
 n=len(p)-1;d=[mul(sub(b,a),n) for a,b in zip(p,p[1:])];dd=[mul(sub(b,a),n-1) for a,b in zip(d,d[1:])];return d,dd
def arc_length(p,n=64):
 d,_=derivatives(p);speed=lambda t:norm(bez(d,t));return (speed(0)+speed(1)+sum((4 if i%2 else 2)*speed(i/n) for i in range(1,n)))/(3*n)
def prepare():
 baseline=[arc_length(control(x['jointDegrees'],H_MIN)) for x in rows]
 target=5*math.ceil(max(baseline)/5)
 result=[]
 for index,x in enumerate(rows):
  q=x['jointDegrees'];lo=H_MIN;hi=800.
  for _ in range(32):
   h=(lo+hi)/2
   if arc_length(control(q,h))<target:lo=h
   else:hi=h
  h=(lo+hi)/2;p=control(q,h);d,dd=derivatives(p);radii=[];speeds=[];pts=[]
  for i in range(101):
   t=i/100;v=bez(d,t);a=bez(dd,t);vnorm=norm(v);den=norm(cross(v,a));radii.append(vnorm**3/den if den>1e-12 else 1e20);speeds.append(vnorm);pts.append(bez(p,t))
  fine=arc_length(p,256)
  result.append({'index':index,'jointDegrees':q,'nativeBlocked':bool(x['nativeShellOriginalBottomIntersectionsMm3']),'bowHeightMm':h,'lengthMm64':arc_length(p),'lengthMm256':fine,'minimumSampledRadiusMm':min(radii),'minimumParametricSpeed':min(speeds),'sampledBounds':[list(map(min,zip(*pts))),list(map(max,zip(*pts)))]})
 report={'accepted':False,'geometryChecked':False,'singleCandidate':{'headFixedStrainPoint':A,'headLeadTangent':TA,'torsoFixedStrainPoint':B,'torsoLeadTangent':TB,'headOutlet':[[-31,23.2,125],[-47,23.2,141],A],'headOutletRadiusMm':16,'headOutletStraightMm':10,'leadControlMm':LEAD,'sideBowDirection':BOW,'minimumBowHeightMm':H_MIN,'constantFlexibleLengthMm':target,'lengthRule':'ceil5(max over all229 source angles of analytic-derivative quadrature length at minimum bow equal to lead96mm); include nativeblocked states, no freedom reduction.','shape':'One degree5Bezier control rule, fixed endpoint tangents, constant-length scalar bow; no per-pose parameter family switching.'},'rows':result,'summary':{'maxMinimumBowLengthMm':max(baseline),'minimumSampledRadiusAllMm':min(r['minimumSampledRadiusMm'] for r in result),'minimumSampledRadiusNativeClearMm':min(r['minimumSampledRadiusMm'] for r in result if not r['nativeBlocked']),'maxLengthQuadratureDiscrepancyMm':max(abs(r['lengthMm256']-target) for r in result),'maxSideBowMm':max(r['bowHeightMm'] for r in result)},'limits':'Sampling radius is a preparation screen, not continuous proof. Root CAD gate must separately check all original obstacles, self-distance, angular sweeps, source wiring lengths, body/header fanouts, physical fixing pieces and assembly sequence. No stock availability or clamp manufacturability claimed.','sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE,Path(__file__)]}}
 (D/'single-candidate-preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary']|{'length':target},indent=2))
if __name__=='__main__':prepare()
