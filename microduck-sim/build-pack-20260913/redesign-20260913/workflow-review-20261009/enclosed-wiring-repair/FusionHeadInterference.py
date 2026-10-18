"""Native independent-body cross-board interference; no unions or geometry mutation."""
import adsk.core,adsk.fusion,json,traceback,time,hashlib
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout')
r={'status':'RUNNING','layoutAccepted':False,'hits':[],'nativeQueries':0,'candidatePairs':0}
def bounds(b):
 q=b.boundingBox;return [[x*10 for x in q.minPoint.asArray()],[x*10 for x in q.maxPoint.asArray()]]
try:
 app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct);assert design.parentDocument.name=='MicroDuck head native packaging repair';root=design.rootComponent
 r['poseSha256']=hashlib.sha256((D/'native-lanes-pose.json').read_bytes()).hexdigest()
 r['actualTransforms']={root.occurrences.item(i).component.name:list(root.occurrences.item(i).transform2.asArray())for i in range(root.occurrences.count)}
 rows={'pi':[],'openrb':[],'cap':[]}
 for i in range(root.allOccurrences.count):
  o=root.allOccurrences.item(i);name=o.fullPathName;k='pi'if name.startswith('Pi Zero W populated group')else 'openrb'if name.startswith('OpenRB manufacturer native solids')else 'cap'if name.startswith('Original closed cap native faceted solid')else None
  if k is None:continue
  for j in range(o.bRepBodies.count):
   b=o.bRepBodies.item(j);assert b.isSolid;rows[k].append((b,name,bounds(b)))
 r['bodyCounts']={k:len(v)for k,v in rows.items()};assert r['bodyCounts']['openrb']==136 and r['bodyCounts']['pi']>=68
 pairgroups=[('pi','openrb'),('openrb','cap')]
 for kindA,kindB in pairgroups:
  for a,an,ab in rows[kindA]:
   for b,bn,bb in rows[kindB]:
    r['candidatePairs']+=1
    if any(ab[1][i]<bb[0][i]or bb[1][i]<ab[0][i]for i in range(3)):continue
    c=adsk.core.ObjectCollection.create();c.add(a);c.add(b);inp=design.createInterferenceInput(c);inp.areCoincidentFacesIncluded=False
    res=design.analyzeInterference(inp);assert res is not None;r['nativeQueries']+=1
    for q in range(res.count):
     part=res.item(q).interferenceBody;assert part
     if part.volume*1000>1e-7:r['hits'].append({'firstKind':kindA,'first':an,'secondKind':kindB,'second':bn,'body':b.name,'volumeMm3':part.volume*1000,'boundsMm':bounds(part)})
   (D/'fusion-head-cross-board.json').write_text(json.dumps(r,indent=2));adsk.doEvents()
 r['status']='NATIVE_CROSS_BOARD_CHECK_COMPLETED';r['crossBoardClear']=not r['hits']
except Exception:r.update(status='CHECK_FAILED',error=traceback.format_exc())
finally:(D/'fusion-head-cross-board.json').write_text(json.dumps(r,indent=2))
