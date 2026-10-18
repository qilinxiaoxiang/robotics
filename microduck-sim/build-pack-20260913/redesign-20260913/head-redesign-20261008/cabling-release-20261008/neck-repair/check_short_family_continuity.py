"""Negative regression: shortest-arc endpoint branch changes at antiparallel tangents."""
from pathlib import Path
import json,math,hashlib
import raised_lateral_worker as w
D=Path(__file__).resolve().parent;rows=[]
for a in [-45.001,-45.,-44.999]:
 t=w.family.terms({'head_yaw':a},w.B,w.U);rows.append({'jointDegrees':{'head_yaw':a},'prefixEnd':t[2],'prefixLengthMm':t[1]})
jump=math.dist(rows[0]['prefixEnd'],rows[-1]['prefixEnd'])
r={'passed':False,'purpose':'Continuous-motion gate beyond discrete229 pose sampling','rows':rows,'jointIncrementDeg':.002,'prefixEndpointJumpMm':jump,'reason':'Shortest direction-conditioning arc uses normalized cross(tangent,bowAxis). At antiparallel directions this normal changes sign, so the selected semicircle jumps to its opposite side. Floating-point cross magnitude at exactly−45 does not repair that geometric discontinuity.','remedyCriterion':'Use a continuous deformation family with explicit bending-plane transport or a controlled intermediate tangent; verify all angular paths. Increasing free length or static sample count cannot repair the branch switch.','sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'raised_lateral_worker.py',D/'finite_anchor_screen.py',D/'single_circle_candidate.py',Path(__file__)]}}
assert jump>60
(D/'short-family-continuity-failure.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
