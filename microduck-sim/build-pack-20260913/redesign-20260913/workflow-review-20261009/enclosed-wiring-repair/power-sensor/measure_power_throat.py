from pathlib import Path
import json,trimesh
from shapely.geometry import MultiLineString,box
from shapely.ops import nearest_points
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor');j=json.loads((D.parents[1]/'original-body-converter/fusion-import-manifest.json').read_text());rows=[]
for y in [-7.6,-3.8]:
 shapes=[]
 for k in ['shell_right','power_support']:
  p=next(p for p in j['parts'] if p['key']==k);m=trimesh.load(p['file'],force='mesh');m.apply_translation(p.get('importTranslationMm',[0,0,0]));s=m.section([0,1,0],[0,y,0]);lines=MultiLineString([[[float(v[0]),float(v[2])] for v in curve] for curve in s.discrete]);shapes.append(lines.intersection(box(-40,30,-24,38.5)))
 p,q=nearest_points(*shapes);width=p.distance(q);rows.append({'yMm':y,'boundaryPointsXZ':[list(p.coords)[0],list(q.coords)[0]],'throatWidthMm':width,'maximumSymmetricRadius3_2ClearanceMm':(width-3.2)/2})
print(json.dumps(rows));(D/'power-throat-section.json').write_text(json.dumps({'method':'Exact triangle-plane sections of both current source surfaces, closest edges in local hook/boss window X[-40,-24], Z[30,38.5]. A necessary local passage bound, not proof of any R6 curve.','rows':rows},indent=2))
