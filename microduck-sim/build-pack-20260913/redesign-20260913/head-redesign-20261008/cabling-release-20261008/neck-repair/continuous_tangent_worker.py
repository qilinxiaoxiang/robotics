"""Evidence-driven side exit revision; frozen previous route remains unchanged."""
import argparse,json,math,sys
from pathlib import Path
import short_domain_worker as domain
import short_path_worker as core
import continuous_tangent_family as family
from single_circle_candidate import arc,line
from prepare_single_candidate import moved,add,mul
D=Path(__file__).resolve().parent;H=D.parent.parent;OUT=D/'continuous-tangent-domain';domain.OUT=OUT;core.OUT=OUT
A=[-47.,45.2,135.];TA=[0,1.,0];B=[0.,-25.,44.];U=[-2**-.5,-2**-.5,0.];L=330.
family.A=A;family.TA=TA
RAWGEOM=core.geom

def geom(i):
 base=json.loads((H/'usb-access/usb-repair/rigid-domain.json').read_text());row={'jointDegrees':{},'nativeShellOriginalBottomIntersectionsMm3':{}} if i==-1 else base['samples'][i];q=row['jointDegrees'];g=family.path(q,L,B)
 if g is None:return row,None
 prefix,pl=arc([-31,23.2,135],[-1,0,0],[0,1,0],16);prefix+=line(prefix[-1],A)[1:];prefix=[moved(p,q) for p in prefix]
 g['points']=prefix+g['points'][1:];g['fixedHeadOutletLengthMm']=pl+6;g['freeLengthMm']=L;g['analyticLengthMm']+=pl+6;return row,g
core.geom=geom

def plan():
 domain.plan();p=json.loads((OUT/'plan.json').read_text());p['inputHashes'][str(Path(__file__).resolve())]=core.sha(Path(__file__));p['inputHashes'][str((D/'head-anchor-v2-screen.json').resolve())]=core.sha(D/'head-anchor-v2-screen.json');p['inputHashes'][str((D/'continuous_tangent_family.py').resolve())]=core.sha(D/'continuous_tangent_family.py');p['inputHashes'][str((D/'short-family-continuity-failure.json').resolve())]=core.sha(D/'short-family-continuity-failure.json');p['parameters']={'A':A,'TA':TA,'B':B,'bowAxis':U,'freeLengthMm':L,'receivingODMm':7,'fixedHeadOutletStart':[-31,23.2,135],'fixedHeadOutletR':16,'fixedHeadOutletStraightMm':6};p['stageScope']='Lateral-tangent revision: complete fixed-head-outlet plus330mm free route across186 native-rigid-clear poses,15 source neck/torso/motor parts. Cap/electronics, terminal fanouts and continuous angular paths remain unvalidated.';p['reason']='The shortest-arc family jumps64mm at yaw−45 despite static pose checks. Fixed55mm integrated tangent transition has no shortest-arc branch and preserves exactanalytic arclength. Diagnostic330mm free wire is not owned150mm stock. Prior225mm endpoint was outside but its downward-tangent conditioning arc entered torso at head_pitch−65. The preceding +Y outlet removed the power_support collision but its fixed elbow still hit shell_left13.297mm3. Raising only the whole fixed outlet10mm inZ targets that contact; body anchorZ44 retainsR13.225. Longer300mm is a diagnostic candidate, not existing150mm stock and no fixture release.';core.save(OUT/'plan.json',p);print(json.dumps({'finalPlanHash':core.sha(OUT/'plan.json'),'parameters':p['parameters']}))

def self_all():
 p=core.current();ph=core.sha(OUT/'plan.json');results=[]
 for i in p['expectedSelfIndices']:
  row,g=geom(i);blocked=bool(row['nativeShellOriginalBottomIntersectionsMm3'])
  if g is None:r={'passed':False,'reason':'Insufficient330mm length for minimum straight reserve','selfComputed':False}
  elif g['minimumCenterRadiusMm']<9:r={'passed':False,'reason':'Centerline bend radius below declaredR9; local-tube self check not applied','minimumCenterRadiusMm':g['minimumCenterRadiusMm'],'selfComputed':False}
  else:r=core.self_one(g['points'])|{'selfComputed':True,'minimumCenterRadiusMm':g['minimumCenterRadiusMm'],'totalLengthMm':g['analyticLengthMm']}
  rec={'pose':i,'planHash':ph,'nativeBaselineBlocked':blocked,'jointDegrees':row['jointDegrees'],**r};core.save(OUT/'self'/f'{i}.json',rec);results.append(rec)
  if not r['passed'] and not blocked:
   core.save(OUT/'self-summary.json',{'planHash':ph,'nativeClearPassed':False,'coverageComplete':False,'expected':229,'completed':len(results),'firstFailure':rec});print(json.dumps(rec));return 2
 clear=[r for r in results if not r['nativeBaselineBlocked']];blocked=[r for r in results if r['nativeBaselineBlocked']];report={'planHash':ph,'nativeClearPassed':all(r['passed'] for r in clear),'coverageComplete':len(results)==229,'expected':229,'completed':len(results),'nativeClearCount':len(clear),'nativeBlockedCount':len(blocked),'nativeBlockedFailures':[r for r in blocked if not r['passed']],'scope':'Native-clear186 self gate; all43 native-blocked results preserved, not certified. Angular paths and solids are separate.','receiptHashes':{str(r['pose']):core.sha(OUT/'self'/f'{r["pose"]}.json') for r in results}};core.save(OUT/'self-summary.json',report);print(json.dumps({k:v for k,v in report.items() if k!='receiptHashes'}))

def passed_self():
 core.current();s=json.loads((OUT/'self-summary.json').read_text());assert s['planHash']==core.sha(OUT/'plan.json') and s['nativeClearPassed'] and s['coverageComplete'];return s
core.passed_self=passed_self
def summary():
 p=core.current();ph=core.sha(OUT/'plan.json');missing=[];stale=[];failed=[];done=0;receipts={}
 for pair in p['expectedPairs']:
  f=OUT/'pairs'/f'{pair["pose"]}__{pair["obstacle"]}.json'
  if not f.exists():missing.append(pair);continue
  r=json.loads(f.read_text());item=next(o for o in p['obstacles'] if o['key']==pair['obstacle']);valid=r['planHash']==ph and r['obstacleSha256']==item['sha256']
  if r['method'].startswith('All receiving-segment'):valid=valid and core.sha(OUT/'centerlines'/f'{pair["pose"]}.json')==r['centerlineFileSha256'] and item['intrinsicSolidValidationReceiptHash']==r['intrinsicSolidValidationReceiptHash']
  else:valid=valid and (OUT/'meshes'/f'{pair["pose"]}.stl').exists() and core.sha(OUT/'meshes'/f'{pair["pose"]}.stl')==r['receivingSha256']
  if not valid:stale.append(pair);continue
  done+=1;receipts[f.name]=core.sha(f)
  if not r['passed']:failed.append(r)
 selfReport=passed_self();complete=not missing and not stale
 report={'wholeHarnessAccepted':False,'planHash':ph,'nativeClear186SelfPassed':True,'nativeBlocked43DiagnosticFailures':selfReport['nativeBlockedFailures'],'expectedPairCount':len(p['expectedPairs']),'completedPairCount':done,'coverageComplete':complete,'nativeClear15PartSubsetClear':complete and not failed,'missingPairs':missing,'stalePairs':stale,'failedPairs':failed,'scope':p['stageScope'],'receiptHashes':receipts}
 core.save(OUT/'summary.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['missingPairs','receiptHashes']},indent=2));return 0 if complete and not failed else 2

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['plan','self','screen','mesh','obstacle','summary']);ap.add_argument('--pose',type=int);ap.add_argument('--key');o=ap.parse_args();core.guard();sys.exit(plan() if o.stage=='plan' else self_all() if o.stage=='self' else domain.screen() if o.stage=='screen' else core.mesh(o.pose) if o.stage=='mesh' else core.obstacle(o.pose,o.key) if o.stage=='obstacle' else summary())
