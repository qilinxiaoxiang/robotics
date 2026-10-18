import adsk.core, adsk.fusion, json, traceback, time, hashlib
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009')
F=P/'fusion-review';F.mkdir(exist_ok=True)

def run(context):
    app=adsk.core.Application.get(); started=time.time(); receipt={'status':'RUNNING','parts':[],'geometry':'current meshes retained as meshes; battery is nominal envelope solid','printReady':False}
    def save(): (F/'fusion-import-receipt.json').write_text(json.dumps(receipt,indent=2))
    try:
        manifestPath=P/'central-cad/fusion-import-manifest.json'
        d=json.loads(manifestPath.read_text()); receipt['manifestSha256']=hashlib.sha256(manifestPath.read_bytes()).hexdigest();save()
        doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.name='MicroDuck C - packaging review'
        design=adsk.fusion.Design.cast(app.activeProduct); root=design.rootComponent
        design.designType=adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        appearance={}
        def color(hexcode):
            if hexcode not in appearance:
                a=design.appearances.add('Review '+hexcode)
                rgb=[int(hexcode[i:i+2],16) for i in (1,3,5)]
                a.color=adsk.core.Color.create(*rgb,255);a.roughness=.65;appearance[hexcode]=a
            return appearance[hexcode]
        groupNames=list(dict.fromkeys(p['group'] for p in d['parts']))
        for group in groupNames:
            occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name=group
            base=comp.features.baseFeatures.add();base.name='Verified world-mm reference meshes';base.startEdit()
            for p in [p for p in d['parts'] if p['group']==group]:
                assert hashlib.sha256(Path(p['file']).read_bytes()).hexdigest()==p['sha256']
                bodies=comp.meshBodies.add(p['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base)
                assert bodies.count==1,p['key']
                b=bodies.item(0);b.name=p['key']+' - '+p['name'];b.appearance=color(p['color'])
                bb=b.boundingBox
                receipt['parts'].append({'key':p['key'],'boundsMm':[[v*10 for v in bb.minPoint.asArray()],[v*10 for v in bb.maxPoint.asArray()]],'mesh':True})
                if group.startswith('Unchanged central'): b.opacity=.22
                if len(receipt['parts'])%15==0:save();adsk.doEvents()
            base.finishEdit()
        battery=d['batterySolid'];xyz=battery['originMinMm'];dims=battery['dimensionsMm']
        occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());bc=occ.component;bc.name='PB1033MI - nominal envelope - original C position'
        planeIn=bc.constructionPlanes.createInput();planeIn.setByOffset(bc.xYConstructionPlane,adsk.core.ValueInput.createByReal(xyz[2]/10));plane=bc.constructionPlanes.add(planeIn)
        sk=bc.sketches.add(plane);sk.name='80.9 x 26 mm battery footprint'
        sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(xyz[0]/10,xyz[1]/10,0),adsk.core.Point3D.create((xyz[0]+dims[0])/10,(xyz[1]+dims[1])/10,0))
        ex=bc.features.extrudeFeatures.addSimple(sk.profiles.item(0),adsk.core.ValueInput.createByReal(dims[2]/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        b=ex.bodies.item(0);b.name=battery['name'];b.appearance=color(battery['color']);b.opacity=.7
        plane.isLightBulbOn=False;sk.isVisible=False
        receipt['batteryBoundsMm']=[[v*10 for v in b.boundingBox.minPoint.asArray()],[v*10 for v in b.boundingBox.maxPoint.asArray()]]
        cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(48,55,35);cam.target=adsk.core.Point3D.create(0,0,0);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.isFitView=True;app.activeViewport.camera=cam
        app.activeViewport.refresh();adsk.doEvents()
        receipt['screenshotSaved']=app.activeViewport.saveAsImageFile(str(F/'C-current-duck-fusion.png'),1600,1200)
        archive=F/'MicroDuck-C-packaging-review.f3d';opts=design.exportManager.createFusionArchiveExportOptions(str(archive));receipt['archiveSaved']=design.exportManager.execute(opts)
        receipt.update(status='COMPLETE',elapsedSeconds=round(time.time()-started,2),nativeMeshBodies=len(receipt['parts']),nativeBatterySolids=1,hasParametricBatteryExtrude=True,fullAssemblyAcceptance=False)
        save()
    except Exception:
        receipt.update(status='ERROR',error=traceback.format_exc(),elapsedSeconds=round(time.time()-started,2));save();app.userInterface.messageBox('MicroDuck import stopped. See fusion-import-receipt.json.\n'+receipt['error'])
