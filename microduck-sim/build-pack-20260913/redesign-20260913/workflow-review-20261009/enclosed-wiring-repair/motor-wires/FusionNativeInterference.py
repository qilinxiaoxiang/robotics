"""Read-only native BRep interference; no imports, conversions, or model edits."""
import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires')
report={'status':'RUNNING','wholeHarnessAccepted':False,'inventory':[],'pairs':[],'meshScope':'Printed/ring reference meshes are NOT inputs to BRep analysis; their independent source-bound static receipt is local-route.json.'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bounds(b):
 q=b.boundingBox;return [[v*10 for v in q.minPoint.asArray()],[v*10 for v in q.maxPoint.asArray()]]
def disjoint(a,b):return any(a[1][i]<b[0][i]or b[1][i]<a[0][i] for i in range(3))
try:
 app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
 assert design.parentDocument.name.startswith('LOCAL ttl-04-03'), 'Wrong active document'
 report['document']=design.parentDocument.name;report['routeSha256']=sha(D/'local-route.json');report['nativeCreationSha256']=sha(D/'fusion-resume-readback.json')
 wires=[];obs=[]
 for i in range(root.allOccurrences.count):
  occ=root.allOccurrences.item(i);name=occ.fullPathName
  kind='wire'if name.startswith('Conductor ')else 'motor'if name.startswith('XL330 native ID')else 'housing'if 'EHR3 receiving envelope'in name else None
  if not kind:continue
  for j in range(occ.bRepBodies.count):
   body=occ.bRepBodies.item(j);assert body.isSolid and body.volume>0
   meta={'occurrence':name,'body':body.name,'kind':kind,'boundsMm':bounds(body),'volumeMm3':body.volume*1000,'rootContext':body.assemblyContext.fullPathName if body.assemblyContext else None}
   report['inventory'].append(meta);(wires if kind=='wire'else obs).append((body,meta))
 assert len(wires)==3 and len([m for _,m in obs if m['kind']=='motor'])==24 and len([m for _,m in obs if m['kind']=='housing'])==2
 pairs=[(a,b)for a in wires for b in obs]+[(wires[i],wires[j])for i in range(3)for j in range(i)]
 for (a,am),(b,bm)in pairs:
  row={'wire':am['occurrence'],'obstacleOccurrence':bm['occurrence'],'obstacleBody':bm['body']}
  if disjoint(am['boundsMm'],bm['boundsMm']):row.update(method='exact body AABB separation',interferenceMm3=0.)
  else:
   entities=adsk.core.ObjectCollection.create();entities.add(a);entities.add(b);inp=design.createInterferenceInput(entities);assert inp;inp.areCoincidentFacesIncluded=False
   res=design.analyzeInterference(inp);assert res is not None
   volumes=[]
   for k in range(res.count):
    rb=res.item(k).interferenceBody;volumes.append(rb.volume*1000 if rb else None)
   assert all(v is not None for v in volumes);row.update(method='Fusion native BRep positive-volume interference',interferenceMm3=sum(volumes),resultVolumesMm3=volumes)
  report['pairs'].append(row)
  (D/'fusion-native-interference.json').write_text(json.dumps(report,indent=2))
 report.update(status='COMPLETED',nativeStaticPassed=all(p['interferenceMm3']<1e-7 for p in report['pairs']),pairCount=len(pairs),exactInterferencePairCount=sum(p['method'].startswith('Fusion')for p in report['pairs']))
except Exception:report.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:(D/'fusion-native-interference.json').write_text(json.dumps(report,indent=2))
