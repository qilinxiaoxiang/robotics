"""1degree neutral-other-joints yaw path; source-bound fixed-material readback."""
import argparse,json,math,hashlib
from pathlib import Path
import raised_body_worker as w
D=Path(__file__).resolve().parent;OUT=D/'raised-body-motion';OUT.mkdir(exist_ok=True)
w.core.guard();ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,required=True);ap.add_argument('--end',type=int,required=True);o=ap.parse_args();assert -170<=o.start<o.end<=170
sources=[Path(__file__),D/'raised_body_worker.py',D/'raised_body_family.py',D/'short_path_worker.py',D/'prepare_single_candidate.py'];hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources};rows=[];prev=None;prevT=None;maxjump=0;maxturn=0;maxChordError=0
for deg in range(o.start,o.end+1):
 q={'head_yaw':deg};g=w.family.path(q,w.L,w.B);row={'headYawDeg':deg,'nativeRigidClassification':'not_recomputed_for_this_intermediate_pose','passed':False}
 if g is None:row['reason']='Insufficient free length'
 elif g['minimumCenterRadiusMm']<9:row.update(reason='Radius belowR9',minimumR=g['minimumCenterRadiusMm'])
 else:
  outlet,pl=w.arc([-31,23.2,135],[-1,0,0],[0,1,0],16);outlet+=w.line(outlet[-1],w.A)[1:];g['points']=[w.moved(p,q) for p in outlet]+g['points'][1:];g['analyticLengthMm']+=pl+6
  row.update(w.core.self_one(g['points']));row['minimumR']=g['minimumCenterRadiusMm'];row['lengthMm']=g['analyticLengthMm'];mat=w.family.material_points(g);row['materialPointCount']=len(mat);chord=sum(math.dist(a,b) for a,b in zip(g['points'],g['points'][1:]));row['fullCurveChordLengthErrorMm']=abs(g['analyticLengthMm']-chord);maxChordError=max(maxChordError,row['fullCurveChordLengthErrorMm']);tans=[[v/math.dist(a,b) for v in [b[k]-a[k] for k in range(3)]] for a,b in zip(mat,mat[1:])]
  if prev is not None:
   jump=max(math.dist(a,b) for a,b in zip(prev,mat));maxjump=max(maxjump,jump);row['maximumMaterialPointStepMm']=jump;turn=max(math.degrees(math.acos(max(-1,min(1,sum(a[k]*b[k] for k in range(3)))))) for a,b in zip(prevT,tans));maxturn=max(maxturn,turn);row['maximumMaterialSecantTurnDeg']=turn
  prev=mat;prevT=tans
 rows.append(row);r={'passed':all(x['passed'] for x in rows),'coverageComplete':deg==o.end,'startDeg':o.start,'endDeg':o.end,'stepDeg':1,'expectedPoses':o.end-o.start+1,'completedPoses':len(rows),'maxMaterialPointStepMm':maxjump,'maxMaterialSecantTurnDegPerOneDegree':maxturn,'maxFullCurveChordLengthErrorMm':maxChordError,'analyticLengthMm':w.L+16*math.pi/2+6,'materialSampleMethod':'501 normalized arclength stations, index order preserved; full fixed-outlet plus free-curve chord length error measured per pose; analytical total length fixed. Secant tangent readback at500 fixed material intervals, not connector identity reassignment.','scope':'Full fixed head outlet and free receiving centerline self/radius/length; no obstacle or intermediate native-rigid clearance claim. Explicit angle-integrated tangent avoids shortest-rotation discontinuity.','sourceHashes':hashes,'rows':rows};(OUT/f'{o.start}_{o.end}.json').write_text(json.dumps(r,indent=2)+'\n')
 if not row['passed']:print(json.dumps(row));raise SystemExit(2)
print(json.dumps({k:v for k,v in r.items() if k not in ['rows','sourceHashes']}))
