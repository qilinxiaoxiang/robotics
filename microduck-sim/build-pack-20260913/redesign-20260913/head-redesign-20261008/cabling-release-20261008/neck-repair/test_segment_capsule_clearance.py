"""Small analytic boxes exercise clear, contact, clipping and incomplete coverage."""
from pathlib import Path
import json,hashlib
import manifold3d as mf
from segment_capsule_clearance import check
D=Path(__file__).resolve().parent;ev={'watertight':True,'positiveVolume':True,'sourceSha256':hashlib.sha256(b'analytic closed cube tests v1').hexdigest()}
rows=[]
for name,center,size,r,expect in [('far',[10,0,0],[2,2,2],1,True),('cross',[.5,0,0],[.2,2,2],1,False),('end-ball-touch',[3,0,0],[2,2,2],1,False),('near-clear',[3.1,0,0],[2,2,2],1,True)]:
 ob=mf.Manifold.cube(size,True).translate(center);x=check([[0,0,0],[1,0,0]],r,0,ob,source_evidence=ev);assert x['passed']==expect,(name,x);rows.append({'name':name,'expected':expect,'result':x})
ob=mf.Manifold.cube([.2,2,2],True).translate([.5,0,0]);x=check([[0,0,0],[1,0,0],[2,0,0]],1,0,ob,source_evidence=ev,stop_on_inconclusive=True);assert not x['passed'] and not x['coverageComplete'] and x['completedSegments']==1;rows.append({'name':'incomplete never passes','result':x})
ob=mf.Manifold.cube([1,1,1],True).translate([0,10,0]);x=check([[0,0,0],[10,10,0]],1,0,ob,source_evidence=ev);assert x['passed'] and x['segments'][0]['gapMayBeSearchCapped'];rows.append({'name':'positive prism gap clipped lower bound','result':x})
r={'passed':True,'tests':rows,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D/'segment_capsule_clearance.py']}};(D/'segment-capsule-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'tests':len(rows)}))
