import adsk.core, adsk.fusion, json, traceback, time, hashlib
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009')
F=P/'fusion-review'
def run(context):
 app=adsk.core.Application.get(); receipt={'status':'RUNNING','printReady':False,'newSolids':[]}; start=time.time()
 def save(): (F/'fusion-skeleton-receipt.json').write_text(json.dumps(receipt,indent=2))
 try:
  design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
  assert sum(o.component.meshBodies.count for o in root.occurrences)==166, 'Expected the current 166-part duck document'
  assert not any(o.component.name.startswith('C lowered8') for o in root.occurrences), 'Already updated'
  app.activeDocument.name='MicroDuck C - native layout and frame skeleton'
  manifest=json.loads((P/'central-cad/fusion-import-manifest.json').read_text()); bykey={x['key']:x for x in manifest['parts']}
  for occ in root.occurrences:
   if occ.component.name.startswith('PB1033MI'):occ.isLightBulbOn=False
   for b in occ.component.meshBodies:
    b.displayOverrides.isSuppressFaceGroupColors=True;b.displayOverrides.isSuppressTriangleEdges=True
    b.opacity=1
    key=b.name.split(' - ')[0]
    if key in bykey:b.appearance=design.appearances.itemByName('Review '+bykey[key]['color'])
  app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle
  app.activeViewport.refresh();adsk.doEvents()
  app.activeViewport.saveAsImageFile(str(F/'C-before-frame-change.png'),1600,1200)
  withdrawn={'torso_base','shell_left','shell_right','power_support','fuse_carrier','regulator_insert','regulator'}
  hidden=[]
  for occ in root.occurrences:
   for b in occ.component.meshBodies:
    key=b.name.split(' - ')[0]
    if key in withdrawn or key.startswith('nut_E-fuse_carrier'):
     b.isLightBulbOn=False;hidden.append(key)
  receipt['withdrawnFromCandidateVisibleScene']=hidden
  specPath=P/'central-cad/central-bridge-primitives.json';spec=json.loads(specPath.read_text());receipt['sourceSha256']=hashlib.sha256(specPath.read_bytes()).hexdigest()
  appearances={}
  def appearance(c):
   if c not in appearances:
    a=design.appearances.add('Frame '+c);a.color=adsk.core.Color.create(*[int(c[i:i+2],16) for i in (1,3,5)],255);a.roughness=.65;appearances[c]=a
   return appearances[c]
  def box(comp,name,xyz,dims,col):
   inp=comp.constructionPlanes.createInput();inp.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(xyz[2]/10));pl=comp.constructionPlanes.add(inp)
   sk=comp.sketches.add(pl);sk.name=name+' footprint'
   sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(xyz[0]/10,xyz[1]/10,0),adsk.core.Point3D.create((xyz[0]+dims[0])/10,(xyz[1]+dims[1])/10,0))
   ex=comp.features.extrudeFeatures.addSimple(sk.profiles.item(0),adsk.core.ValueInput.createByReal(dims[2]/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);ex.name=name
   b=ex.bodies.item(0);b.name=name;b.appearance=appearance(col);pl.isLightBulbOn=False;sk.isVisible=False
   bounds=[[v*10 for v in b.boundingBox.minPoint.asArray()],[v*10 for v in b.boundingBox.maxPoint.asArray()]]
   assert max(abs(bounds[0][i]-xyz[i]) for i in range(3))<1e-5
   assert max(abs(bounds[1][i]-xyz[i]-dims[i]) for i in range(3))<1e-5
   receipt['newSolids'].append({'name':name,'boundsMm':bounds,'parametricExtrusion':True});return b
  occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name='C lowered8 - nominal battery - both ends open'
  bank=spec['batterySolid'];box(comp,bank['name'],bank['originMinMm'],bank['dimensionsMm'],'#56a9d4')
  occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name='Central frame LOAD PATH ONLY - incomplete seats and holes'
  for p in spec['primitiveSolids']:box(comp,p['key'],p['originMinMm'],p['dimensionsMm'],p['color'])
  cam=app.activeViewport.camera;cam.eye=adsk.core.Point3D.create(48,55,35);cam.target=adsk.core.Point3D.create(0,0,0);cam.upVector=adsk.core.Vector3D.create(0,0,1);cam.cameraType=adsk.core.CameraTypes.OrthographicCameraType;cam.isFitView=True;app.activeViewport.camera=cam
  app.activeViewport.refresh();adsk.doEvents();app.activeViewport.saveAsImageFile(str(F/'C-frame-candidate.png'),1600,1200)
  archive=F/'MicroDuck-C-native-review.f3d';receipt['archiveSaved']=design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
  receipt.update(status='COMPLETE',elapsedSeconds=round(time.time()-start,2),fullAssemblyAcceptance=False,remaining=['lower hip seats','neck bearing profiles','battery retention','converter location','screw stacks','joint motion','physical fit']);save()
 except Exception:
  receipt.update(status='ERROR',error=traceback.format_exc());save();app.userInterface.messageBox(receipt['error'])
