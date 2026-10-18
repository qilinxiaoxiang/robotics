"""Bounded standard-library neck-harness mathematics. No CAD imports or fit claims."""
from pathlib import Path
import argparse,hashlib,json,math,time
from prepare_single_candidate import moved,add,sub,mul,dot,cross,norm,rot
D=Path(__file__).resolve().parent;H=D.parent.parent
SOURCE=H/'usb-access/usb-repair/rigid-domain.json'
A=[-47.,23.2,103.];B=[26.,38.,42.];TA=[0.,0.,-1.];TB=[0.,0.,-1.]
RMIN=9.;OD=7.
def unit(v):return mul(v,1/norm(v))
def angle(a,b):return math.acos(max(-1.,min(1.,dot(unit(a),unit(b)))))
def max_chord_projection(L,alpha,beta,R):
 # Curvature bound: angle to chord >= max(0, alpha-s/R, beta-(L-s)/R).
 crossing=(L+R*(alpha-beta))/2
 first=max(0.,min(L,R*alpha,crossing));last=max(0.,L-max(0.,L-R*beta,crossing))
 return L-first-last+R*(math.sin(alpha)-math.sin(alpha-first/R)+math.sin(beta)-math.sin(beta-last/R))
def lower_bound(a,ta):
 e=unit(sub(B,a));d=norm(sub(B,a));alpha=angle(ta,e);beta=angle(TB,e)
 lo=d;hi=d+2*math.pi*RMIN
 for _ in range(60):
  m=(lo+hi)/2
  if max_chord_projection(m,alpha,beta,RMIN)<d:lo=m
  else:hi=m
 return {'chordMm':d,'tangentCurvatureNecessaryLengthMm':max(hi,RMIN*angle(ta,TB)),'startAngleToChordDegrees':math.degrees(alpha),'endAngleToChordDegrees':math.degrees(beta)}
u0=unit(sub(B,A));n0=unit(sub([0.,1.,0.],mul(u0,dot([0.,1.,0.],u0))))
def frame(e):
 cr=cross(u0,e);s=norm(cr);c=dot(u0,e)
 if c < -.999: raise ValueError('Reference frame antipodal: no branch switch accepted')
 n=n0 if s<1e-12 else rot(n0,mul(cr,1/s),math.atan2(s,c))
 return n,cross(e,n)
def controls(a,ta,h,amp,twist):
 e=unit(sub(B,a));n,v=frame(e)
 return [a,add(a,mul(ta,h)),add(add(a,mul(ta,2*h)),add(mul(n,amp),mul(v,twist*amp))),add(sub(B,mul(TB,2*h)),sub(mul(n,amp),mul(v,twist*amp))),sub(B,mul(TB,h)),B]
def coefficients(n,t):return [math.comb(n,i)*t**i*(1-t)**(n-i) for i in range(n+1)]
WEIGHTS={n:[(coefficients(5,i/n),coefficients(4,i/n),coefficients(3,i/n)) for i in range(n+1)] for n in [32,128]}
def eval_at(p,w):return [sum(c*x[k] for c,x in zip(w,p)) for k in range(3)]
def derivatives(p):
 d=[mul(sub(y,x),5) for x,y in zip(p,p[1:])];dd=[mul(sub(y,x),4) for x,y in zip(d,d[1:])];return d,dd
def length(p,n=32):
 d,_=derivatives(p);speeds=[norm(eval_at(d,w[1])) for w in WEIGHTS[n]]
 return (speeds[0]+speeds[-1]+sum((4 if i%2 else 2)*speeds[i] for i in range(1,n)))/(3*n)
def candidate(q,L,h,twist):
 a=moved(A,q);ta=moved(TA,q,True);lb=lower_bound(a,ta);base=controls(a,ta,h,0,twist);l0=length(base)
 if l0>L:return {'candidateAvailable':False,'failure':'Zero-amplitude length exceeds target','zeroAmplitudeLengthMm':l0,**lb}
 hi=80.;upper=controls(a,ta,h,hi,twist)
 if length(upper)<L:return {'candidateAvailable':False,'failure':'Required amplitude exceeds finite 80 mm bound','zeroAmplitudeLengthMm':l0,**lb}
 lo=0.
 # Arc length is convex in amplitude. Starting at an accepted amplitude0,
 # exactly one outward crossing exists before upper; no grid/random search.
 for _ in range(25):
  mid=(lo+hi)/2
  if length(controls(a,ta,h,mid,twist))<L:lo=mid
  else:hi=mid
 amplitude=(lo+hi)/2;p=controls(a,ta,h,amplitude,twist);d,dd=derivatives(p);pts=[];radii=[];speeds=[]
 for w,wd,wdd in WEIGHTS[128]:
  pts.append(eval_at(p,w));dv=eval_at(d,wd);ddv=eval_at(dd,wdd);speed=norm(dv);den=norm(cross(dv,ddv));speeds.append(speed);radii.append(speed**3/den if den>1e-12 else 1e20)
 bounds=[list(map(min,zip(*pts))),list(map(max,zip(*pts)))];fine=length(p,128)
 return {'candidateAvailable':True,'controlPoints':p,'amplitudeMm':amplitude,'lengthMm128':fine,'lengthErrorMm':fine-L,'minimumSampledCenterRadiusMm':min(radii),'minimumParametricSpeed':min(speeds),'sampledReceivingBounds':[[x-OD/2 for x in bounds[0]],[x+OD/2 for x in bounds[1]]],'mathScreenPass':min(radii)>=RMIN and min(speeds)>1 and abs(fine-L)<.05,**lb}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--length',type=float,default=200);ap.add_argument('--handle',type=float,default=24);ap.add_argument('--twist',type=float,default=.5);op=ap.parse_args();t=time.time();source=json.loads(SOURCE.read_text());rows=[]
 for i,row in enumerate(source['samples']):
  result=candidate(row['jointDegrees'],op.length,op.handle,op.twist)
  rows.append({'index':i,'jointDegrees':row['jointDegrees'],'nativeBaselineBlocked':bool(row['nativeShellOriginalBottomIntersectionsMm3']),**result})
 available=[r for r in rows if r['candidateAvailable']];clear=[r for r in rows if not r['nativeBaselineBlocked']]
 summary={'expectedPoseCount':229,'completedPoseCount':len(rows),'coverageComplete':len(rows)==229,'candidateAvailableCount':len(available),'mathScreenPassCount':sum(r.get('mathScreenPass',False) for r in rows),'nativeClearCount':len(clear),'nativeClearMathScreenPassCount':sum(r.get('mathScreenPass',False) for r in clear),'maxChordMm':max(r['chordMm'] for r in rows),'maxTangentCurvatureNecessaryLengthMm':max(r['tangentCurvatureNecessaryLengthMm'] for r in rows),'minimumSampledCenterRadiusMm':min((r['minimumSampledCenterRadiusMm'] for r in available),default=None),'maxAmplitudeMm':max((r['amplitudeMm'] for r in available),default=None),'elapsedSeconds':time.time()-t}
 report={'accepted':False,'CADExecuted':False,'family':'Single continuous 3D quintic Bezier, fixed endpoint tangents, transported transverse frame, symmetric lateral and antisymmetric twist offsets. One scalar amplitude preserves length; no intermediate electrical connector or planar-ribbon constraint.','parameters':{'headAnchorNeutral':A,'headTangentNeutral':TA,'torsoAnchor':B,'torsoIncomingTangent':TB,'headOutletProposal':{'start':[-31,23.2,125],'R16TurnFrom':[-1,0,0],'R16TurnToward':[0,0,-1],'arcEnd':[-47,23.2,109],'straightMm':6,'arcPlusStraightLengthMm':16*math.pi/2+6,'CADClear':False},'targetFlexibleLengthMm':op.length,'endpointBezierHandleMm':op.handle,'twistToSideAmplitudeRatio':op.twist,'finiteAmplitudeBoundsMm':[0,80],'receivingODMm':OD,'minimumCenterRadiusScreenMm':RMIN},'lowerBoundMeaning':'Necessary lower bound only from chord projection under |curvature|<=1/R9 and endpoint tangent turning. It ignores solids, self-distance, endpoint fanouts and head-outlet fixed length.','screenMeaning':'129 sampled curve points and Simpson32/128 arc lengths are mathematical rejection screens, not continuous curvature proof or geometric acceptance. All229 source poses preserved including43 native-blocked. Angular transition paths still unrun.','summary':summary,'rows':rows,'sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,Path(__file__),D/'prepare_single_candidate.py']}}
 path=D/('short-family-L%g-H%g-T%g.json'%(op.length,op.handle,op.twist));path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
