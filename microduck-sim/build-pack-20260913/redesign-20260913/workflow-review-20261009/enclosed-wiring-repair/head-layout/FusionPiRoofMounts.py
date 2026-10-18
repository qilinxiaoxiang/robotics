"""Native cap-to-Pi mounting study. Exact upstream cap plus editable four roof bosses."""
import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout')
O=D/'pi-roof-mounts';O.mkdir(exist_ok=True)
r={'status':'RUNNING','accepted':False,'holesWorldMm':[[47.5,-30],[47.5,28],[70.5,-30],[70.5,28]],'holeEvidence':'Source Pi PCB circular boundaries: 144 vertices per hole at radius1.35 mm after adopted Pi-only pose; board Z130.7..132.3 mm.','fasteners':'4 M2x6 with side-loaded M2 nuts; no washers','physicalFitVerified':False}
def save(): (O/'native-readback.json').write_text(json.dumps(r,indent=2))
def point(x,y,z):return adsk.core.Point3D.create(x/10,y/10,z/10)
try:
 app=adsk.core.Application.get();name='MicroDuck Pi roof mounts native study';docs=[app.documents.item(i)for i in range(app.documents.count)if app.documents.item(i).name==name];assert not docs,'Existing study must be inspected before rerunning'
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name=name;design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;root=design.rootComponent
 source=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());source.component.name='Exact original cap reference'
 assert app.importManager.importToTarget(app.importManager.createSTEPImportOptions(str(D/'sources/top-head-native.step')),source.component)
 originals=[source.component.bRepBodies.item(i)for i in range(source.component.bRepBodies.count)]
 for q in source.component.allOccurrences:
  originals.extend(q.bRepBodies.item(i)for i in range(q.bRepBodies.count))
 assert len(originals)==1 and originals[0].isSolid
 temp=adsk.fusion.TemporaryBRepManager.get();copy=temp.copy(originals[0]);matrix=adsk.core.Matrix3D.create();assert matrix.setWithArray([0,-1,0,2.61,1,0,0,0,0,0,1,11.11146,0,0,0,1]);assert temp.transform(copy,matrix)
 source.isLightBulbOn=False
 occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name='Closed cap with integral Pi mounting bosses'
 base=comp.features.baseFeatures.add();base.startEdit()
 try:cap=comp.bRepBodies.add(copy,base)
 finally:base.finishEdit()
 cap=comp.bRepBodies.item(0);cap.name='Original closed cap';r['originalVolumeMm3']=cap.volume*1000
 def sketch_at(z,name):
  inp=comp.constructionPlanes.createInput();assert inp.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(z/10));pl=comp.constructionPlanes.add(inp);sk=comp.sketches.add(pl);sk.name=name;return sk,pl
 sk,pl=sketch_at(132.3,'Four Pi PCB seating bosses - native to-body extent')
 for x,y in r['holesWorldMm']:sk.sketchCurves.sketchCircles.addByCenterRadius(point(x,y,0),.35)
 assert sk.profiles.count==4
 profiles=adsk.core.ObjectCollection.create()
 for i in range(sk.profiles.count):profiles.add(sk.profiles.item(i))
 inp=comp.features.extrudeFeatures.createInput(profiles,adsk.fusion.FeatureOperations.JoinFeatureOperation)
 extent=adsk.fusion.ToEntityExtentDefinition.create(cap,True)
 assert inp.setOneSideExtent(extent,adsk.fusion.ExtentDirections.PositiveExtentDirection)
 inp.participantBodies=[cap];feature=comp.features.extrudeFeatures.add(inp);assert feature and feature.bodies.count==1
 cap=feature.bodies.item(0);sk.isVisible=False;pl.isLightBulbOn=False;r['afterBossVolumeMm3']=cap.volume*1000;save()
 sk,pl=sketch_at(132.3,'M2 clearance blind bores - 5 mm')
 for x,y in r['holesWorldMm']:sk.sketchCurves.sketchCircles.addByCenterRadius(point(x,y,0),.11)
 ps=adsk.core.ObjectCollection.create()
 for i in range(sk.profiles.count):ps.add(sk.profiles.item(i))
 inp=comp.features.extrudeFeatures.createInput(ps,adsk.fusion.FeatureOperations.CutFeatureOperation);inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(.5)),adsk.fusion.ExtentDirections.PositiveExtentDirection);inp.participantBodies=[cap];f=comp.features.extrudeFeatures.add(inp);cap=f.bodies.item(0);sk.isVisible=False;pl.isLightBulbOn=False
 sk,pl=sketch_at(134.3,'Side load M2 nuts - 4.2 mm flat spacing and 1.8 mm height')
 for x,y in r['holesWorldMm']:sk.sketchCurves.sketchLines.addTwoPointRectangle(point(x-4,y-2.1,0),point(x+2.5,y+2.1,0))
 ps=adsk.core.ObjectCollection.create()
 for i in range(sk.profiles.count):ps.add(sk.profiles.item(i))
 inp=comp.features.extrudeFeatures.createInput(ps,adsk.fusion.FeatureOperations.CutFeatureOperation);inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(.18)),adsk.fusion.ExtentDirections.PositiveExtentDirection);inp.participantBodies=[cap];f=comp.features.extrudeFeatures.add(inp);cap=f.bodies.item(0);sk.isVisible=False;pl.isLightBulbOn=False
 assert cap.isSolid and comp.bRepBodies.count==1
 archive=O/'MicroDuck-Pi-roof-mounts.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 step=O/'closed-cap-with-pi-bosses.step';assert design.exportManager.execute(design.exportManager.createSTEPExportOptions(str(step),comp))
 stl=O/'closed-cap-with-pi-bosses-world.stl';opts=design.exportManager.createSTLExportOptions(cap,str(stl));opts.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh;assert design.exportManager.execute(opts)
 r.update(status='NATIVE_MOUNTS_CREATED_NEIGHBOR_AND_TOOL_CHECK_PENDING',finalVolumeMm3=cap.volume*1000,archive=str(archive),step=str(step),stl=str(stl),sourceSha256=hashlib.sha256((D/'sources/top-head-native.step').read_bytes()).hexdigest(),scope='Native exact cap with four parametric bosses, blind screw bores and side-load nut pockets. No claimed complete populated closure.')
 app.activeViewport.fit()
except Exception:r.update(status='FAILED_NOT_ACCEPTED',error=traceback.format_exc())
finally:save()
