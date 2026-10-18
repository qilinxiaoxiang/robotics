"""Strict circular-wire separation for one closed non-contact obstacle."""
import argparse,json,math,sys
from pathlib import Path
import bounded_amp_check as c
import check_speaker_rewire as s
import precision_mesh as pm
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire';P=D/'speaker-rewire-amp16z2p0-proposal.json';MOD=H/'cabling-release-20261008/neck-repair/segment_capsule_clearance.py';sys.path.insert(0,str(MOD.parent));from segment_capsule_clearance import check
p=argparse.ArgumentParser();p.add_argument('--wire',type=int,choices=[0,1],required=True);p.add_argument('--key',required=True);p.add_argument('--clearance',type=float,default=0);a=p.parse_args();assert a.key not in ['speaker','amplifier'],'Contact endpoints need separate flat shoulder proof';c.guarded_import();route=json.loads(P.read_text())['routes'][a.wire];scene=json.loads((O/'scene-plan.json').read_text());row=scene['rows'][a.key];f=Path(row.get('path') or row['dataFile']);ob=s.solid(row);pts=route['centerlineMm'];maxchord=max(math.dist(x,y) for x,y in zip(pts,pts[1:]));assert maxchord<=.250001;R=min(x['radiusMm'] for x in route['analyticSegments'] if x['kind']=='arc');sag=R-math.sqrt(R*R-(maxchord/2)**2)+1e-8
# Loader validates closed STL; data-only parts constructed by same validated Mesh64 path.
if row.get('path'):
 mesh=c.tm.load(f,force='mesh');assert mesh.is_watertight and mesh.volume>0
else:assert ob.status()==c.mf.Error.NoError and ob.volume()>0
r=check(pts,.75+a.clearance,sag,ob,source_evidence={'watertight':True,'positiveVolume':True,'sourceSha256':c.sha(f)},stop_on_inconclusive=False);r.update(wire=a.wire,obstacle=a.key,physicalWireRadiusMm=.75,additionalClearanceTargetMm=a.clearance,maxCenterlineChordMm=maxchord,minimumAnalyticRadiusMm=R,inputHashes=c.fingerprint([Path(__file__),MOD,P,O/'scene-plan.json',f]),integrationReady=False);c.atomic_json(O/(f'round-distance-{a.wire}-{a.key}'+(f'-clearance{a.clearance}' if a.clearance else '')+'.json'),r);print(json.dumps({k:v for k,v in r.items() if k not in ['segments','inputHashes']}));raise SystemExit(0 if r['passed'] else 2)
