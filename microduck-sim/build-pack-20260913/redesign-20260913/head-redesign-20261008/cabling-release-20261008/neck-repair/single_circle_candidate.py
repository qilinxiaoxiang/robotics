"""Single side-guided constant-length circular family; pure standard library.

The head outlet direction is first turned toward global+Y by a fixed-radius
arc. A two-quarter-circle U then joins the resulting point to the body anchor.
All remaining length is in two straight legs. There is no spline, no curvature
optimization and no per-pose family switch. CAD clearance is deliberately unset.
"""
from pathlib import Path
import math,json,hashlib
from prepare_single_candidate import moved,add,sub,mul,dot,cross,norm,rot
D=Path(__file__).resolve().parent;H=D.parent.parent;BASE=H/'usb-access/usb-repair/rigid-domain.json'
A=[-47.,23.2,151.];B=[-66.,50.,35.];Y=[0.,1,0];R=16.;MIN_STRAIGHT=8.
def unit(p):return mul(p,1/norm(p))
def arc(p,t,u,r,step=.5):
 angle=math.acos(max(-1.,min(1.,dot(t,u))))
 if angle<1e-10:return [p],0.
 axis=unit(cross(t,u));center=add(p,mul(cross(axis,t),r));v=sub(p,center);n=max(2,math.ceil(angle*r/step))
 return [add(center,rot(v,axis,angle*i/n)) for i in range(n+1)],angle*r
def line(a,b,step=.5):
 n=max(1,math.ceil(norm(sub(b,a))/step));return [add(a,mul(sub(b,a),i/n)) for i in range(n+1)]
def terms(q):
 a=moved(A,q);ta=moved([0,0,1],q,True);prefix,pl=arc(a,ta,Y,R);c=prefix[-1];delta=sub(B,c);delta[1]=0.;d=norm(delta);rr=min(R,d/2)
 return a,prefix,pl,c,delta,d,rr

def candidate(q,total_length):
 a,prefix,pl,c,delta,d,rr=terms(q);e=unit(delta)
 # U arcs: +Y -> chord direction e -> -Y. Radius decreases only if chord<2R.
 core=total_length-pl;across=d-2*rr;left=(core-across-math.pi*rr-c[1]+B[1])/2;right=left+c[1]-B[1]
 if min(left,right)<MIN_STRAIGHT-1e-7:raise ValueError('Insufficient straight reserve')
 pts=prefix[:];top=add(c,mul(Y,left));pts+=line(c,top)[1:]
 pp,l1=arc(top,Y,e,rr);pts+=pp[1:];across_end=add(pp[-1],mul(e,across));pts+=line(pp[-1],across_end)[1:]
 pp,l2=arc(across_end,e,mul(Y,-1),rr);pts+=pp[1:];pts+=line(pp[-1],B)[1:]
 exact=pl+left+right+across+l1+l2
 return {'points':pts,'lengthMm':exact,'prefixLengthMm':pl,'coreRadiusMm':rr,'minimumCenterRadiusMm':min(R,rr),'straightLegsMm':[left,right],'acrossStraightMm':across,'endpointErrorMm':norm(sub(pts[-1],B)),'headFixedPoint':a,'torsoFixedPoint':B,'pieceLengthsMm':[pl,left,l1,across,l2,right]}

def prepare():
 base=json.loads(BASE.read_text());minimums=[];first=[]
 for b in base['samples']:
  q=b['jointDegrees'];a,p,pl,c,delta,d,rr=terms(q);need=pl+d+(math.pi-2)*rr+abs(c[1]-B[1])+2*MIN_STRAIGHT;minimums.append(need);first.append((d,rr))
 target=5*math.ceil(max(minimums)/5);rows=[]
 for i,b in enumerate(base['samples']):
  r=candidate(b['jointDegrees'],target);pts=r.pop('points');r.update(index=i,jointDegrees=b['jointDegrees'],nativeBlocked=bool(b['nativeShellOriginalBottomIntersectionsMm3']),bounds=[list(map(min,zip(*pts))),list(map(max,zip(*pts)))],chordLengthMm=sum(norm(sub(bb,aa)) for aa,bb in zip(pts,pts[1:])))
  assert abs(r['lengthMm']-target)<1e-7 and r['endpointErrorMm']<1e-7
  rows.append(r)
 out={'accepted':False,'geometryChecked':False,'family':'FixedR16 direction-conditioning arc + planar two-quarter-circleU + variable straight legs; all pieces tangent-continuous; exacttotalarclength','headFixedNeutralPoint':A,'headOutletRadiusMm':16,'headOutletStraightMm':10,'torsoFixedPoint':B,'torsoOutwardTangent':Y,'maximumCircleRadiusMm':R,'minimumStraightReserveMm':MIN_STRAIGHT,'receivingDiameterMm':7,'constantFlexibleLengthMm':target,'lengthRule':'Roundup5(max over ALL229 unfiltered poses of prefix+chord+(pi-2)*coreRadius+abs(endpointYdifference)+16). No jointrange reduction.','minimumCenterRadiusAllMm':min(x['minimumCenterRadiusMm'] for x in rows),'minimumCenterRadiusNativeClearMm':min(x['minimumCenterRadiusMm'] for x in rows if not x['nativeBlocked']),'minimumInnerRadiusBoundMm':min(x['minimumCenterRadiusMm'] for x in rows)-3.5,'rows':rows,'fixingRequirements':['Headstrainpoint at[-47,23.2,151] needs removable rear guide and twoattachmentpoints; no printedclip designedorvalidatedyet.','Bodystrainpoint[-66,50,35] needs rigidbracket fixedto torso/IMUguard withendpointtangent+Y. Itisnot actualIMUsocket.','Circle conditioning arc and twoUarcs are free servicewire shaping, not a claimed mechanicalmotion actuator; physicalwire shapevariation/fatigue still requires validation.'],'stillRequired':['Fullnativeobstacles andallcurrentreceivingparts','Wire-wire and route selfdistance','1degreeangularpaths withunchanged length','Pin/socketfanouts andmotorbus separateconnections','Actualcutlength/availablewireextension source','Clipgeometryandinstallation/closure/toolaccess'],'sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE,Path(__file__),D/'prepare_single_candidate.py']}}
 (D/'single-circle-candidate.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['constantFlexibleLengthMm','minimumCenterRadiusAllMm','minimumCenterRadiusNativeClearMm','minimumInnerRadiusBoundMm']},indent=2))
if __name__=='__main__':prepare()
