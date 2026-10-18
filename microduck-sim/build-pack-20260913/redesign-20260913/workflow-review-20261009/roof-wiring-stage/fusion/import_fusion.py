import adsk.core,adsk.fusion,json,hashlib,time,traceback
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/roof-wiring-stage/fusion')
app=adsk.core.Application.get();start=time.time();receipt={'status':'RUNNING','parts':[],'printReady':False,'physicalVerified':False}
def save(): (P/'fusion-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def bounds(b,occ):
 bb=b.createForAssemblyContext(occ).boundingBox
 return [[v*10 for v in bb.minPoint.asArray()],[v*10 for v in bb.maxPoint.asArray()]]
def capture(name,eye,target,extent,root,head=False,opened=False,ghost=False):
 for o in root.occurrences:
  for b in o.component.meshBodies:
   key=b.name.split(' - ')[0];p=bykey[key]
   b.isLightBulbOn=not(head and (p['expectedFinalBoundsMm'][1][2]<93 or (p.get('isWire') and p['expectedFinalBoundsMm'][0][2]<95)))
   if key=='head_cap' and opened:b.isLightBulbOn=False
   b.opacity=.16 if ghost and not p.get('isWire') and key not in ['pi','openrb','camera_board','amplifier','speaker'] else 1
 cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(*eye);cam.target=adsk.core.Point3D.create(*target);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.setExtents(extent*4/3,extent);cam.isFitView=False;app.activeViewport.camera=cam;app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle;app.activeViewport.refresh();adsk.doEvents();app.activeViewport.saveAsImageFile(str(P/name),1600,1200)
try:
 manifest=P/'fusion-import-manifest.json';d=json.loads(manifest.read_text());receipt['manifestSha256']=hashlib.sha256(manifest.read_bytes()).hexdigest();bykey={p['key']:p for p in d['parts']}
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MicroDuck - restored roof and routed wiring - stage review'
 design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;design.designType=adsk.fusion.DesignTypes.ParametricDesignType;design.fusionUnitsManager.distanceDisplayUnits=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
 colors={}
 def appearance(c):
  if c not in colors:
   a=design.appearances.add('Part '+c);a.color=adsk.core.Color.create(*[int(c[i:i+2],16) for i in (1,3,5)],255);a.roughness=.65;colors[c]=a
  return colors[c]
 for group in dict.fromkeys(p['group'] for p in d['parts']):
  parts=[p for p in d['parts'] if p['group']==group];shift=parts[0]['importTranslationMm'];assert all(p['importTranslationMm']==shift for p in parts)
  xf=adsk.core.Matrix3D.create();xf.translation=adsk.core.Vector3D.create(*[x/10 for x in shift]);occ=root.occurrences.addNewComponent(xf);comp=occ.component;comp.name=group
  base=comp.features.baseFeatures.add();base.name='Source-bound millimeter geometry';base.startEdit()
  for p in parts:
   assert hashlib.sha256(Path(p['file']).read_bytes()).hexdigest()==p['sha256'],p['key']
   bodies=comp.meshBodies.add(p['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert bodies.count==1
   b=bodies.item(0);b.name=p['key']+' - '+p['name'];b.appearance=appearance(p['color']);b.opacity=1;b.displayOverrides.isSuppressFaceGroupColors=True;b.displayOverrides.isSuppressTriangleEdges=True
   bb=bounds(b,occ);err=max(abs(bb[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3));assert err<.002,(p['key'],bb,err)
   receipt['parts'].append({'key':p['key'],'boundsMm':bb,'maxErrorMm':err})
  base.finishEdit();adsk.doEvents()
 n=len(d['parts']);assert len(receipt['parts'])==n
 capture('head-closed.png',(28,32,31),(2.5,0,13),15,root,head=True)
 capture('head-wires.png',(-28,-32,35),(2.5,0,13),16,root,head=True,opened=True,ghost=True)
 capture('whole-wiring.png',(-48,55,28),(0,0,0),39,root,ghost=True)
 capture('whole-closed.png',(48,55,35),(0,0,0),39,root)
 archive=P/'MicroDuck-roof-and-wiring-stage.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
 readDoc=app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(str(archive)));readDoc.name=doc.name
 readDesign=adsk.fusion.Design.cast(app.activeProduct);readback=[]
 for o in readDesign.rootComponent.occurrences:
  for b in o.component.meshBodies:
   key=b.name.split(' - ')[0];p=bykey[key];bb=bounds(b,o);err=max(abs(bb[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3));assert err<.002,(key,err);readback.append({'key':key,'maxErrorMm':err})
 assert len(readback)==n
 capture('head-closed-readback.png',(28,32,31),(2.5,0,13),15,readDesign.rootComponent,head=True)
 capture('whole-closed-readback.png',(48,55,35),(0,0,0),39,readDesign.rootComponent)
 receipt.update(status='COMPLETE',savedArchive=str(archive),archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),readbackPassed=True,readback=readback,meshBodies=n,wireBodies=sum(bool(p.get('isWire')) for p in d['parts']),elapsedSeconds=round(time.time()-start,2),motorBus='Mac USB directly to OpenRB; Pi sensor transport remains to be implemented',runtimeMigrated=False)
 save()
 for old in list(app.documents):
  if old!=readDoc and (old==doc or old.name.startswith('MicroDuck original body') or old.name.startswith('MicroDuck - restored roof and routed wiring')):old.close(False)
except Exception:
 receipt.update(status='ERROR',error=traceback.format_exc());save();app.userInterface.messageBox(receipt['error'])
