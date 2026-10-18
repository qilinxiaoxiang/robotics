"""Read-only source audit; no CAD imports, route generation, or scene edits."""
from pathlib import Path
import json, hashlib, plistlib, platform
D=Path(__file__).resolve().parent
OLD=D.parents[1]/'roof-wiring-stage/motor-wires'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
causes={
 'ttl-openrb-15':'Unqualified forward/down corridor crosses motor13, jaw_support and head_yaw_link; a separate short rise touches a roof feature. Registered OpenRB socket is not the board-centre shortcut.',
 'ttl-15-14':'Cross-head bridge traverses speaker/keeper; rear descent crosses cap and bottom. A separate conservative motor14 plug receiving box also contacts bottom and needs profile-level resolution.',
 'ttl-14-13':'Local upper turn clips jaw_support and yaw-link tops. This demonstrates an invalid route, not absence of all feasible paths.',
 'ttl-13-11':'Negative-Y descending corridor traverses jaw-support arm, bottom and jaw frame rather than an established opening.',
 'ttl-05-04':'Rear X approximately -30 vertical track occupies restored converter insert and power support.',
 'ttl-04-03':'Straight channel traverses motor3 rear/bottom, right plate and thigh lip. Rounded waypoints remain inside obstacles; sampled radius 0.066 mm is also inadmissibly tight for the modeled 0.75 mm conductor radius.',
 'ttl-02-01':'Knee exit clips thigh lip; ankle-side turn crosses lower-link rear bar.',
 'ttl-01-06':'Both ankle exit turns intersect ankle/inner rings and lower links, before the cross-leg span.',
 'ttl-06-07':'Mirrored knee/thigh lip and lower-link rear-bar crossings.',
 'ttl-08-09':'Mirrored motor8, plate and thigh-lip channel error; sampled 0.066 mm radius is not a valid bend acceptance.',
 'ttl-09-10':'Mirrored rear track occupies restored converter insert and power support.'}
s=json.loads((OLD/'stage-summary.json').read_text())
rows=[]
for r in s['routes']:
 checked=Path(r['checkFile']); assert sha(checked)==r['checkSha256']
 by={}
 for c in r['sourceMeshInterferences']:
  if c['obstacle'] not in by or c['intersectionMm3']>by[c['obstacle']]['maximumSingleBodyIntersectionMm3']:
   by[c['obstacle']]={'maximumSingleBodyIntersectionMm3':c['intersectionMm3'],'boundsMm':c['boundsMm'],'routePart':c['part']}
 rows.append({'id':r['id'],'neutralStaticClear':r['neutralStaticCollisionFree'],'rootCauseInterpretation':causes.get(r['id'],'No source-mesh intersection in this neutral static receipt; not complete harness acceptance.'),'evidenceClass':'existing exact intersection receipt; corridor cause is geometric interpretation','obstacleMaxima':by,'conservativeObstacleContacts':r['conservativeObstacleContacts'],'unresolvedInputs':r['unresolvedInputs'],'lengthMm':r['routeLengthMm'],'sampledMinimumRadiusMm':r['minimumSampledCenterlineBendRadiusMm'],'spareLengthModeled':r['spareLengthModeled'],'receipt':str(checked),'receiptSha256':sha(checked)})
apps=[]
for root in [Path('/Applications'),Path.home()/'Applications']:
 for p in root.glob('*.app'):
  if any(q in p.name.lower() for q in ['fusion','inventor','solidwork','freecad','parallels','vmware']):
   info=p/'Contents/Info.plist'
   d=plistlib.loads(info.read_bytes()) if info.exists() else {}
   apps.append({'path':str(p),'bundleId':d.get('CFBundleIdentifier'),'bundleVersion':d.get('CFBundleShortVersionString'),'versionScope':'bundle/launcher, not verified CAD engine or license'})
a={'verifiedDate':'2026-10-09','status':'diagnostic_only_no_route_changes','wholeHarnessAccepted':False,'sourceHashes':{str(OLD/f):sha(OLD/f) for f in ['stage-summary.json','manifest.json','build_routes.py']},'counts':{'routes':15,'neutralStaticClear':4,'knownFailed':11},'machineInventory':{'platform':platform.platform(),'searchedAppDirectories':['/Applications',str(Path.home()/'Applications')],'matches':apps,'scopeLimit':'No entitlement audit or exhaustive installation search. VideoFusion is not CAD. No installed Inventor/SOLIDWORKS found in these app roots.'},'rootCauses':rows,'generatorFinding':{'file':str(OLD/'build_routes.py'),'cornerTrimExpression':'min(2.5,nv*.3,nw*.3)','problem':'Heuristic trim does not enforce specified minimum bend radius; invalid waypoint corridors survive replacement of free cubic curves by rounded polylines.'},'remainingAcceptance':['actual wire OD and permitted bend radius','stock spare length, restraints and service loops','plug insertion and prewired closure','joint motion with admissible flexible deformation','pin order and branch power isolation']}
(D/'tool-and-route-diagnostic.json').write_text(json.dumps(a,indent=2)+'\n')
print('15 source-bound routes checked; 11 geometric failures retained; no CAD performed.')
