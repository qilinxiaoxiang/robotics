import adsk.core,adsk.fusion,json,time,traceback,hashlib
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair')
a=adsk.core.Application.get();r={'status':'STARTED'}
def save(): (P/'native-shell-readback.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 project=next(p for p in a.data.dataProjects if p.name=='Default Project')
 identity=json.loads((P/'native-shell-upload.json').read_text())['dataFileId']
 file=project.rootFolder.dataFiles.itemById(identity)
 r['dataFileId']=identity;r['isComplete']=file.isComplete;save()
 doc=a.documents.open(file,True);design=adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'));root=design.rootComponent
 bodies=list(root.bRepBodies)
 for occ in root.allOccurrences:bodies.extend(list(occ.bRepBodies))
 r['bodies']=[{'name':b.name,'isSolid':b.isSolid,'faces':b.faces.count,'volumeMm3':b.volume*1000,'boundsMm':[[x*10 for x in b.boundingBox.minPoint.asArray()],[x*10 for x in b.boundingBox.maxPoint.asArray()]],'surfaceTypes':sorted(set(str(f.geometry.surfaceType) for f in b.faces))} for b in bodies]
 r['meshBodies']=root.meshBodies.count+sum(o.component.meshBodies.count for o in root.allOccurrences)
 assert bodies and all(b.isSolid for b in bodies),'No complete solid body imported'
 step=P/'head-layout/sources/top-head-native.step';f3d=P/'head-layout/sources/top-head-native.f3d';stl=P/'head-layout/sources/top-head-native.stl'
 ex=design.exportManager
 assert ex.execute(ex.createSTEPExportOptions(str(step)))
 assert ex.execute(ex.createFusionArchiveExportOptions(str(f3d)))
 opts=ex.createSTLExportOptions(root,str(stl));opts.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementMedium;assert ex.execute(opts)
 a.activeViewport.fit();a.activeViewport.refresh();adsk.doEvents();a.activeViewport.saveAsImageFile(str(P/'head-layout/sources/native-head-source.png'),1400,1000)
 r['exports']=[{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in [step,f3d,stl]]
 r['status']='FACETED_SOLID_IMPORT_VERIFIED';save()
except Exception:r.update(status='ERROR',error=traceback.format_exc());save()
