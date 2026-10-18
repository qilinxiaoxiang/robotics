import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/pi-roof-mounts');r=json.loads((D/'native-readback.json').read_text())
try:
 app=adsk.core.Application.get();docs=[d for d in app.documents if d.name=='MicroDuck Pi roof mounts native study'];assert len(docs)==1;docs[0].activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
 occ=next(o for o in root.occurrences if o.component.name=='Closed cap with integral Pi mounting bosses');comp=occ.component;cap=comp.bRepBodies.item(0)
 src=next(o for o in root.occurrences if o.component.name=='Exact original cap reference');bodies=[b for b in src.component.bRepBodies]
 for q in src.component.allOccurrences:bodies.extend(b for b in q.bRepBodies)
 assert len(bodies)==1
 temp=adsk.fusion.TemporaryBRepManager.get();copy=temp.copy(bodies[0]);m=adsk.core.Matrix3D.create();m.setWithArray([0,-1,0,2.61,1,0,0,0,0,0,1,11.11146,0,0,0,1]);assert temp.transform(copy,m)
 ref=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());ref.component.name='Exact original roof stop - preserve exterior';base=ref.component.features.baseFeatures.add();base.startEdit()
 try:rb=ref.component.bRepBodies.add(copy,base)
 finally:base.finishEdit()
 rb=ref.component.bRepBodies.item(0).createForAssemblyContext(ref);ref.isLightBulbOn=False
 inp=comp.constructionPlanes.createInput();inp.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(13.23));pl=comp.constructionPlanes.add(inp);sk=comp.sketches.add(pl);sk.name='Flat sides clear full GPIO housings up to exact original roof'
 for ymin,ymax in [(-27.45,-25.5),(23.5,25.45)]:sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(6.64,ymin/10,0),adsk.core.Point3D.create(7.46,ymax/10,0))
 ps=adsk.core.ObjectCollection.create()
 for p in sk.profiles:ps.add(p)
 inp=comp.features.extrudeFeatures.createInput(ps,adsk.fusion.FeatureOperations.CutFeatureOperation);inp.setOneSideExtent(adsk.fusion.ToEntityExtentDefinition.create(rb,True),adsk.fusion.ExtentDirections.PositiveExtentDirection);inp.participantBodies=[cap];f=comp.features.extrudeFeatures.add(inp);f.name='GPIO clearance limited by original closed roof';cap=f.bodies.item(0);assert cap.isSolid and comp.bRepBodies.count==1;sk.isVisible=False;pl.isLightBulbOn=False
 assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(r['archive']));assert design.exportManager.execute(design.exportManager.createSTEPExportOptions(r['step'],comp));opts=design.exportManager.createSTLExportOptions(cap,r['stl']);opts.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh;assert design.exportManager.execute(opts)
 r['gpioBossRelief']['extent']='Native up-to-original-body: clear entire header/female-housing height, preserve original closed roof';r['finalVolumeMm3']=cap.volume*1000;r['archiveSha256']=hashlib.sha256(Path(r['archive']).read_bytes()).hexdigest();r['status']='NATIVE_FULL_HEIGHT_RELIEF_CREATED_PENDING_CHECK'
except Exception:r.update(status='FULL_RELIEF_FAILED',error=traceback.format_exc())
finally:(D/'native-readback.json').write_text(json.dumps(r,indent=2))
