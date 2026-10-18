import adsk.core,adsk.fusion,json,hashlib,time,traceback
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/original-body-converter')
app=adsk.core.Application.get();start=time.time();receipt={'status':'RUNNING','parts':[],'printReady':False,'physicalVerified':False}
def save(): (P/'fusion-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
try:
 manifest=P/'fusion-import-manifest.json';d=json.loads(manifest.read_text());receipt['manifestSha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MicroDuck original body - DFR1202 in battery location'
 design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;design.designType=adsk.fusion.DesignTypes.ParametricDesignType;design.fusionUnitsManager.distanceDisplayUnits=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
 colors={}
 def appearance(c):
  if c not in colors:
   a=design.appearances.add('Part '+c);a.color=adsk.core.Color.create(*[int(c[i:i+2],16) for i in (1,3,5)],255);a.roughness=.65;colors[c]=a
  return colors[c]
 for group in dict.fromkeys(p['group'] for p in d['parts']):
  parts=[p for p in d['parts'] if p['group']==group];shift=parts[0]['importTranslationMm'];assert all(p['importTranslationMm']==shift for p in parts)
  xf=adsk.core.Matrix3D.create();xf.translation=adsk.core.Vector3D.create(*[x/10 for x in shift]);occ=root.occurrences.addNewComponent(xf);comp=occ.component;comp.name=group
  base=comp.features.baseFeatures.add();base.name='Source-bound millimeter meshes';base.startEdit()
  for p in parts:
   assert hashlib.sha256(Path(p['file']).read_bytes()).hexdigest()==p['sha256']
   bodies=comp.meshBodies.add(p['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert bodies.count==1
   b=bodies.item(0);b.name=p['key']+' - '+p['name'];b.appearance=appearance(p['color']);b.opacity=1;b.displayOverrides.isSuppressFaceGroupColors=True;b.displayOverrides.isSuppressTriangleEdges=True
   proxy=b.createForAssemblyContext(occ);bb=proxy.boundingBox
   bounds=[[v*10 for v in bb.minPoint.asArray()],[v*10 for v in bb.maxPoint.asArray()]]
   err=max(abs(bounds[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3));assert err<.001,(p['key'],bounds,err)
   receipt['parts'].append({'key':p['key'],'boundsMm':bounds,'maxErrorMm':err})
  base.finishEdit();adsk.doEvents()
 assert len(receipt['parts'])==161
 def view(eye,target,path):
  cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(*eye);cam.target=adsk.core.Point3D.create(*target);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.isFitView=True;app.activeViewport.camera=cam;app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle;app.activeViewport.refresh();adsk.doEvents();app.activeViewport.saveAsImageFile(str(P/path),1600,1200)
 view((48,55,35),(0,0,0),'original-body-front.png')
 view((-48,55,28),(0,0,0),'original-body-rear.png')
 view((48,55,35),(0,0,0),'original-body-front.png')
 archive=P/'MicroDuck-original-body-converter.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 # Reopen saved file; check component transforms and mesh bounds through their root proxies.
 readDoc=app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(str(archive)));readDoc.name='MicroDuck original body - DFR1202 in battery location'
 readDesign=adsk.fusion.Design.cast(app.activeProduct);bykey={p['key']:p for p in d['parts']};readback=[]
 for o in readDesign.rootComponent.occurrences:
  for b in o.component.meshBodies:
   key=b.name.split(' - ')[0];p=bykey[key];bb=b.createForAssemblyContext(o).boundingBox;bounds=[[v*10 for v in bb.minPoint.asArray()],[v*10 for v in bb.maxPoint.asArray()]];err=max(abs(bounds[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3));assert err<.001,(key,err);readback.append({'key':key,'maxErrorMm':err})
 assert len(readback)==161
 view((48,55,35),(0,0,0),'original-body-readback.png')
 receipt.update(status='COMPLETE',savedArchive=str(archive),archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),readbackPassed=True,readback=readback,meshBodies=161,hipYawSpacingMm=35,hipPitchSpacingMm=85,elapsedSeconds=round(time.time()-start,2),newPrintGeometry=False)
 save()
 for old in list(app.documents):
  if old!=readDoc and (old==doc or old.name=='MicroDuck C - native layout review'):old.close(False)
except Exception:
 receipt.update(status='ERROR',error=traceback.format_exc());save();app.userInterface.messageBox(receipt['error'])
