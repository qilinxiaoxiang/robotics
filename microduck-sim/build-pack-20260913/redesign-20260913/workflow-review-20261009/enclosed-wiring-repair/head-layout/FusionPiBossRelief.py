import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/pi-roof-mounts');r=json.loads((D/'native-readback.json').read_text())
try:
 app=adsk.core.Application.get();assert app.activeDocument.name=='MicroDuck Pi roof mounts native study';design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;occ=next(o for o in root.occurrences if o.component.name=='Closed cap with integral Pi mounting bosses');comp=occ.component;assert comp.bRepBodies.count==1;cap=comp.bRepBodies.item(0)
 for mountSketch in comp.sketches:
  if mountSketch.name=='Four Pi PCB seating bosses - native to-body extent':
   for circle in mountSketch.sketchCurves.sketchCircles:circle.radius=.4
 design.computeAll();cap=comp.bRepBodies.item(0)
 assert not any(f.name=='GPIO base flat clearance 0.45 mm' for f in comp.features.extrudeFeatures),'Relief already applied'
 inp=comp.constructionPlanes.createInput();inp.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(13.23));plane=comp.constructionPlanes.add(inp);sk=comp.sketches.add(plane);sk.name='Clear physical GPIO base; preserve nut floor and 0.45 mm minimum side wall'
 for ymin,ymax in [(-27.45,-25.5),(23.5,25.45)]:sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(6.69,ymin/10,0),adsk.core.Point3D.create(7.41,ymax/10,0))
 ps=adsk.core.ObjectCollection.create()
 for p in sk.profiles:ps.add(p)
 inp=comp.features.extrudeFeatures.createInput(ps,adsk.fusion.FeatureOperations.CutFeatureOperation);inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(.29)),adsk.fusion.ExtentDirections.PositiveExtentDirection);inp.participantBodies=[cap];f=comp.features.extrudeFeatures.add(inp);f.name='GPIO base flat clearance 0.45 mm';cap=f.bodies.item(0);assert cap.isSolid and comp.bRepBodies.count==1;sk.isVisible=False;plane.isLightBulbOn=False
 assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(r['archive']));assert design.exportManager.execute(design.exportManager.createSTEPExportOptions(r['step'],comp));opts=design.exportManager.createSTLExportOptions(cap,r['stl']);opts.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh;assert design.exportManager.execute(opts)
 r['gpioBossRelief']={'nativeFeature':f.name,'minimumNominalHeaderGapMm':.45,'bossDiameterMm':8,'headerFacingNutWallMm':.45,'nutFloorMm':2,'rangeZMm':[132.3,135.2]};r['finalVolumeMm3']=cap.volume*1000;r['archiveSha256']=hashlib.sha256(Path(r['archive']).read_bytes()).hexdigest();r['status']='NATIVE_BOSS_BASE_RELIEF_CREATED_PENDING_CHECK'
except Exception:r.update(status='RELIEF_FAILED',error=traceback.format_exc())
finally:(D/'native-readback.json').write_text(json.dumps(r,indent=2))
