"""Separate native bought-part bodies; no Boolean consolidation or optimizer."""
import adsk.core,adsk.fusion,json,hashlib,traceback,time
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair')
M=D/'head-layout/native-fusion-repair-inputs.json';R=D/'head-layout/fusion-native-packaging.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def matrix(T):
 arr=[x for row in T for x in row]
 for i in [3,7,11]:arr[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(arr);return m
I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
out={'status':'IMPORTING_FAILED_POSE_FOR_REPAIR','layoutAccepted':False,'parts':[],'inputSha256':sha(M)}
def save():R.write_text(json.dumps(out,indent=2))
try:
 cfg=json.loads(M.read_text());app=adsk.core.Application.get();name='MicroDuck head native packaging repair'
 docs=[app.documents.item(i)for i in range(app.documents.count)if app.documents.item(i).name==name];assert len(docs)<=1
 if docs:doc=docs[0];doc.activate()
 else:doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name=name
 design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;design.designType=adsk.fusion.DesignTypes.ParametricDesignType
 def getcomp(parent,key,T):
  found=[parent.occurrences.item(i)for i in range(parent.occurrences.count)if parent.occurrences.item(i).component.name==key];assert len(found)<=1
  if found:return found[0]
  occ=parent.occurrences.addNewComponent(matrix(T));occ.component.name=key;return occ
 rb=cfg['openrb'];assert sha(rb['file'])==rb['sha256'];occ=getcomp(root,'OpenRB manufacturer native solids',rb['nativeToFailedPartition'])
 if occ.component.bRepBodies.count==0 and occ.component.allOccurrences.count==0:assert app.importManager.importToTarget(app.importManager.createSTEPImportOptions(rb['file']),occ.component)
 rbBodies=[occ.component.bRepBodies.item(i)for i in range(occ.component.bRepBodies.count)]
 for o in [occ.component.allOccurrences.item(i)for i in range(occ.component.allOccurrences.count)]:
  rbBodies.extend(o.bRepBodies.item(j)for j in range(o.bRepBodies.count))
 rbcount=sum(b.isSolid for b in rbBodies);assert rbcount>100,('Manufacturer native solid count',rbcount)
 out['openrbNativeSolidCount']=rbcount;save()
 pi=getcomp(root,'Pi Zero W populated group',cfg['piCurrentWorldToFailedPartition'])
 for p in cfg['piParts']:
  assert sha(p['file'])==p['sha256'],p['key'];T=[r[:]for r in I]
  for i in range(3):T[i][3]=p['sourceTranslationMm'][i]
  child=getcomp(pi.component,p['key'],T);comp=child.component
  if comp.bRepBodies.count==0:
   if not comp.meshBodies.count:
    base=comp.features.baseFeatures.add();base.startEdit()
    try:meshes=comp.meshBodies.add(p['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert meshes.count>0
    finally:base.finishEdit()
   inp=comp.features.meshConvertFeatures.createInput([comp.meshBodies.item(i)for i in range(comp.meshBodies.count)])
   inp.meshConvertMethodType=adsk.fusion.MeshConvertMethodTypes.FacetedMeshConvertMethodType
   feature=comp.features.meshConvertFeatures.add(inp);assert feature
  count=comp.bRepBodies.count;assert count>0
  volumes=[]
  for j in range(count):
   b=comp.bRepBodies.item(j);assert b.isSolid and b.volume>0,(p['key'],b.name);volumes.append(b.volume*1000)
  for j in range(comp.meshBodies.count):comp.meshBodies.item(j).isLightBulbOn=False
  comp.attributes.add('MicroDuck','source',json.dumps({'key':p['key'],'sha256':p['sha256'],'geometryRole':p['geometryRole']}))
  out['parts'].append({'key':p['key'],'nativeSolidCount':count,'volumeMm3':sum(volumes),'geometryType':'Faceted BRep from source STL; not reconstructed feature history','sourceSha256':p['sha256']});save();adsk.doEvents()
 archive=D/'head-layout/MicroDuck-head-native-packaging.f3d'
 assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 out.update(status='NATIVE_INDEPENDENT_BODIES_READY_FOR_POSITION_REPAIR',archive=str(archive),archiveSha256=sha(archive))
 cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(18,-20,22);cam.target=adsk.core.Point3D.create(4,0,14);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.isFitView=True;app.activeViewport.camera=cam;app.activeViewport.refresh()
except Exception:out.update(status='FAILED_IMPORT_NOT_ACCEPTED',error=traceback.format_exc())
finally:save()
