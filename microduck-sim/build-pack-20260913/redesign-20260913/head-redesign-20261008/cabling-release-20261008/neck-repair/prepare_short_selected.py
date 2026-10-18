"""Selected compact round-harness family. Stdlib math only, no CAD/fit release."""
from pathlib import Path
import json,math,hashlib,time
from finite_anchor_screen import terms,path,A,TA,SOURCE,H
from prepare_single_candidate import moved,sub,norm,mul,dot
import short_continuous_family as bounds_math
from check_local_pair_stdlib import dist
D=Path(__file__).resolve().parent
B=[0.,-25.,47.];U=[-2**-.5,-2**-.5,0.];L=215.;OD=7.;RMIN=9.
bounds_math.B=B;bounds_math.TB=mul(U,-1)
def self_screen(points):
 # Adjacent centerline neighborhoods of <=14 mm cannot cross a Ø7 tube
 # under this candidate's exact per-piece minimum R>=9; all other pairs tested.
 segments=list(zip(points,points[1:]));arcs=[0.]
 sagitta=RMIN-math.sqrt(RMIN**2-(.5/2)**2)
 diameter=OD+2*sagitta  # Enclose the exact circular arcs outside their chords.
 for a,b in segments:arcs.append(arcs[-1]+norm(sub(b,a)))
 exact=0;fail=[]
 for i,(a,b) in enumerate(segments):
  for j in range(i+1,len(segments)):
   if arcs[j]-arcs[i+1]<=14:continue
   c,d=segments[j]
   if any(max(min(a[k],b[k]),min(c[k],d[k]))-min(max(a[k],b[k]),max(c[k],d[k]))>=diameter for k in range(3)):continue
   exact+=1;gap=dist(a,b,c,d)
   if gap<diameter:
    fail.append({'segments':[i,j],'centerDistanceMm':gap})
    if len(fail)==20:return {'passed':False,'exactCandidatePairsChecked':exact,'conservativeDistanceThresholdMm':diameter,'firstFailures':fail,'truncated':True}
 return {'passed':not fail,'exactCandidatePairsChecked':exact,'conservativeDistanceThresholdMm':diameter,'firstFailures':fail,'truncated':False}
def main():
 start=time.time();base=json.loads(SOURCE.read_text());rows=[]
 for i,r in enumerate(base['samples']):
  q=r['jointDegrees'];p=path(q,B,U,L);assert p is not None;pts=p.pop('points');lb=bounds_math.lower_bound(moved(A,q),moved(TA,q,True));prefix=terms(q,B,U)[1]
  rows.append({'index':i,'jointDegrees':q,'nativeBaselineBlocked':bool(r['nativeShellOriginalBottomIntersectionsMm3']),'requiredLengthMm':terms(q,B,U)[-1],'endpointConditioningAngleDegrees':math.degrees(prefix/16),**p,**lb})
 clear=[r for r in rows if not r['nativeBaselineBlocked']]
 indices={-1,max(rows,key=lambda r:r['requiredLengthMm'])['index'],min(rows,key=lambda r:r['minimumCenterRadiusMm'])['index'],min(clear,key=lambda r:r['minimumCenterRadiusMm'])['index'],68,136}
 tests=[]
 for i in sorted(indices):
  q={} if i==-1 else rows[i]['jointDegrees'];p=path(q,B,U,L);tests.append({'index':i,'jointDegrees':q,'nativeBaselineBlocked':False if i==-1 else rows[i]['nativeBaselineBlocked'],**self_screen(p['points'])})
 neutral=path({},B,U,L);pts=neutral.pop('points');(D/'short-selected-neutral-centerline.json').write_text(json.dumps({'points':pts,'spacingMaxMm':.5},separators=(',',':'))+'\n')
 def group(rs):return {'poses':len(rs),'mathPathsAvailable':len(rs),'minimumExactCenterRadiusMm':min(r['minimumCenterRadiusMm'] for r in rs),'maxAnalyticLengthDriftMm':max(abs(r['analyticLengthMm']-L) for r in rs),'maxChordMm':max(r['chordMm'] for r in rs),'maxNecessaryTangentLengthBoundMm':max(r['tangentCurvatureNecessaryLengthMm'] for r in rs),'maxEndpointConditioningAngleDegrees':max(r['endpointConditioningAngleDegrees'] for r in rs),'receivingBoundsUnion':[[min(r['receivingBounds'][0][k] for r in rs) for k in range(3)],[max(r['receivingBounds'][1][k] for r in rs) for k in range(3)]]}
 report={'accepted':False,'CADExecuted':False,'candidate':'One continuous cable with a spatial endpoint-conditioning R16 arc, followed by one rear/left U composed of exact tangent quarter-circles and straight legs. U plane follows endpoints; no ribbon-plane constraint or intermediate electrical connection.','headAnchorNeutral':A,'headOutwardTangentNeutral':TA,'bodyAnchor':B,'bodyIncomingTangent':mul(U,-1),'bowAxis':U,'constantFlexibleSpanMm':L,'receivingODMm':OD,'minimumCenterRadiusCriterionMm':RMIN,'fixedHeadOutletLengthMm':16*math.pi/2+6,'minimumTotalBeforeTerminalFanoutsMm':L+16*math.pi/2+6,'current4397MaximumSpanMm':160,'current4397CanDeliver':False,'neutral':neutral,'neutralGoals':{'XminAtLeast':-95,'absoluteYmaxAtMost':80,'ZmaxAtMost':140,'flexibleLengthAtMost':240},'groups':{'all229':group(rows),'nativeClear186':group(clear),'nativeBlocked43':group([r for r in rows if r['nativeBaselineBlocked']])},'finiteSelfScreen':{'expectedPoseIndices':sorted(indices),'completedPoseIndices':[r['index'] for r in tests],'allSelectedPassed':all(r['passed'] for r in tests),'scope':'These selected poses only; no all229 or angular-path self acceptance. Exact polyline distance at max arc/chord spacing0.5mm; pair distance threshold includes twice the R9 worst-case sagitta to enclose the exact arcs.','results':tests},'rows':rows,'stillRequired':['Head downward R16 outlet and body guide actual geometry, then each actual obstacle at each pose','Complete self and twist-continuity check over186 native-clear poses plus angular paths; retain43 rigid-blocked diagnostics separately','Actual fixed/moving anchor strain-relief and connector-before-closure order','Current Pi/amp fanouts, motor bus separate paths','Stock continuous lead or explicit supported extension; actual wire gauge, I2C integrity, fatigue and physical commissioning'],'nextCADInputs':'Current method local candidate + unified amplifier/cap manifests; no published geometry mutation. Start with neutral self, then one obstacle at a time under512MiB/120s only after root token.','sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,Path(__file__),D/'finite_anchor_screen.py',D/'short_continuous_family.py',D/'single_circle_candidate.py',D/'prepare_single_candidate.py',D/'check_local_pair_stdlib.py']},'elapsedSeconds':time.time()-start}
 (D/'short-selected-preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['constantFlexibleSpanMm','minimumTotalBeforeTerminalFanoutsMm','neutral','groups','finiteSelfScreen','elapsedSeconds']},indent=2))
if __name__=='__main__':main()
