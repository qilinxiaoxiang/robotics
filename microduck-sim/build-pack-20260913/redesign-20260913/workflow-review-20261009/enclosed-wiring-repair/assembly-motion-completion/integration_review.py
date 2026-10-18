import copy,hashlib,importlib.util,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent;G=D.parents[2]/'leg-guide-20261006';sys.path.insert(0,str(G));sys.path.insert(0,str(D))
from check_delta import data
from assembly_motion_overlay import apply_motion_overlay
base,effective,service=data();ap=D/'assembly-motion-overlay.json';result,serv=apply_motion_overlay(effective,service,ap)
ops=[o for m in result['modules'] if m['id'] in ['left-leg','right-leg','neck'] for o in m['operations']]+serv['module']['operations']
fixture={'operations':ops,'parts':[{k:v for k,v in p.items() if not k.endswith('B64')} for p in result['parts']],'screws':result['screws']}
(D/'integration-fixture.json').write_text(json.dumps(fixture,separators=(',',':')))
# A patch-content change must invalidate a reviewed receipt, even when the base
# operation still matches. This runs the real applier, not a mirrored check.
mutation=json.loads(ap.read_text());patch=next(p for p in mutation['operationPatches'] if p['operationId']=='left-leg-09');patch['set']['moveKeys'].remove('foot');test=D/'integration-mutated-overlay.json';test.write_text(json.dumps(mutation))
try:apply_motion_overlay(effective,service,test)
except (ValueError,AssertionError):accepted=False
else:accepted=True
finally:test.unlink()
report={'unverifiedPatchMutationAccepted':accepted,'sources':{str(G/f):hashlib.sha256((G/f).read_bytes()).hexdigest() for f in ['assembly_motion_overlay.py','bundle_guide.py','viewer.js','test_assembly_phases.cjs']}}
(D/'integration-source-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
