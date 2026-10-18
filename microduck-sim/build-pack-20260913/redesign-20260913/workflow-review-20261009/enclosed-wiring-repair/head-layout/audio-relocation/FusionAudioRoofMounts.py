"""Increment the existing Pi roof native study; no new document or exterior opening.
Inherited M2.5 tapping interface is engineering intent, not a proven plastic thread.
Execute this file once; it calls run() at its end and resumes named features.
"""
import adsk.core,adsk.fusion,json,hashlib,traceback,time
from pathlib import Path
O=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/audio-relocation')
D=O.parent;R=D.parents[2];H=R/'head-redesign-20261008';OUT=O/'native';OUT.mkdir(exist_ok=True)
SPEC=O/'native-mount-spec.json';RECEIPT=OUT/'native-audio-readback.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def matrix(T):
 a=[v for row in T for v in row]
 for i in [3,7,11]:a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
def point(x,y):return adsk.core.Point3D.create(x/10,y/10,0)
def bbox(b):q=b.preciseBoundingBox;return [[v*10 for v in q.minPoint.asArray()],[v*10 for v in q.maxPoint.asArray()]]
def run():
 t0=time.time();cfg=json.loads(SPEC.read_text());prior=json.loads(RECEIPT.read_text())if RECEIPT.exists() else None;r=prior or {'status':'RUNNING','features':[],'printReady':False,'wholeHeadAccepted':False,'physicalFitVerified':False,'specSha256':sha(SPEC)}
 r.update(status='RUNNING',scriptSha256=sha(O/'FusionAudioRoofMounts.py'));r.pop('error',None)
 def save():RECEIPT.write_text(json.dumps(r,indent=2)+'\n')
 try:
  assert r['specSha256']==sha(SPEC),'Changed feature specification requires an explicit native update'
  for p,h in cfg['sourceHashes'].items():assert sha(p)==h,('Changed source',p)
  app=adsk.core.Application.get();docs=[d for d in app.documents if d.name=='MicroDuck Pi roof mounts native study'];assert len(docs)==1;docs[0].activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
  occ=next(o for o in root.occurrences if o.component.name=='Closed cap with integral Pi mounting bosses');comp=occ.component;assert comp.bRepBodies.count==1;cap=comp.bRepBodies.item(0)
  stop=next(o for o in root.occurrences if o.component.name=='Exact original roof stop - preserve exterior');assert stop.component.bRepBodies.count==1;original=stop.component.bRepBodies.item(0).createForAssemblyContext(stop)
  r.setdefault('beforeVolumeMm3',cap.volume*1000);r.setdefault('beforeBoundsMm',bbox(cap));r['documentName']=docs[0].name;save()
  def existing(name):return [f for f in comp.features.extrudeFeatures if f.name==name]
  def circle(z,x,y,rad,name):
   p=comp.constructionPlanes.createInput();p.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(z/10));pl=comp.constructionPlanes.add(p);sk=comp.sketches.add(pl);sk.name=name;sk.sketchCurves.sketchCircles.addByCenterRadius(point(x,y),rad/10);assert sk.profiles.count==1;return sk,pl
  for spec in cfg['mounts']:
   assert spec['exactBoreDiskOuterRoofMinZMm']-spec['seatZMm']-spec['pilotDepthMm']>=.6,'Roof minimum axial skin must remain at least0.6mm for this local design'
   for operation in ['boss','pilot']:
    name='Audio '+spec['id']+' '+operation;found=existing(name);assert len(found)<=1
    if found:continue
    z=spec['seatZMm'];rad=spec['bossDiameterMm']/2 if operation=='boss' else spec['pilotDiameterMm']/2
    sk,pl=circle(z,*spec['xyMm'],rad,name);kind=adsk.fusion.FeatureOperations.JoinFeatureOperation if operation=='boss' else adsk.fusion.FeatureOperations.CutFeatureOperation;ex=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),kind)
    if operation=='boss':extent=adsk.fusion.ToEntityExtentDefinition.create(original,True)
    else:
     pn='audio_'+spec['id']+'_pilotDepth';p=design.userParameters.itemByName(pn)
     if not p:p=design.userParameters.add(pn,adsk.core.ValueInput.createByString(str(spec['pilotDepthMm'])+' mm'),'mm','Blind pilot depth; source roof skin retained')
     extent=adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString(pn))
    assert ex.setOneSideExtent(extent,adsk.fusion.ExtentDirections.PositiveExtentDirection);ex.participantBodies=[cap];before=cap.volume*1000;f=comp.features.extrudeFeatures.add(ex);assert f;f.name=name;assert comp.bRepBodies.count==1;cap=comp.bRepBodies.item(0);assert cap.isSolid;after=cap.volume*1000;assert after>before if operation=='boss' else after<before
    sk.isVisible=False;pl.isLightBulbOn=False;r['features'].append({'name':name,'beforeMm3':before,'afterMm3':after,'nativeFeatureToken':f.entityToken});save()
  # One local head-bearing pad on the original cradle, not a moved speaker assembly.
  cm=cfg['cradle'];name='Speaker cradle - one lowered screw seat';found=[o for o in root.occurrences if o.component.name==name];assert len(found)<=1
  co=found[0]if found else root.occurrences.addNewComponent(adsk.core.Matrix3D.create());co.component.name=name;cc=co.component
  if cc.bRepBodies.count==0:
   base=cc.features.baseFeatures.add();base.startEdit()
   try:ms=cc.meshBodies.add(cm['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert ms.count==1
   finally:base.finishEdit()
   cv=cc.features.meshConvertFeatures.createInput([cc.meshBodies.item(0)]);cv.meshConvertMethodType=adsk.fusion.MeshConvertMethodTypes.FacetedMeshConvertMethodType;assert cc.features.meshConvertFeatures.add(cv)
   for m in cc.meshBodies:m.isLightBulbOn=False
  assert cc.bRepBodies.count==1;cb=cc.bRepBodies.item(0)
  fn='Single speaker screw seat +0.95mm into interior'
  if not any(f.name==fn for f in cc.features.extrudeFeatures):
   plin=cc.constructionPlanes.createInput();plin.setByOffset(cc.xYConstructionPlane,adsk.core.ValueInput.createByReal(cm['seatBottomZMm']/10));pl=cc.constructionPlanes.add(plin);sk=cc.sketches.add(pl);sk.name=fn
   for radius in [cm['outerRadiusMm'],cm['holeRadiusMm']]:sk.sketchCurves.sketchCircles.addByCenterRadius(point(*cm['xyMm']),radius/10)
   profile=max((sk.profiles.item(i)for i in range(sk.profiles.count)),key=lambda p:p.areaProperties().area)
   ex=cc.features.extrudeFeatures.createInput(profile,adsk.fusion.FeatureOperations.JoinFeatureOperation);ex.setDistanceExtent(False,adsk.core.ValueInput.createByReal(cm['extrudeDepthMm']/10));ex.participantBodies=[cb];before=cb.volume*1000;f=cc.features.extrudeFeatures.add(ex);assert f;f.name=fn;assert cc.bRepBodies.count==1;cb=cc.bRepBodies.item(0);assert cb.isSolid;sk.isVisible=False;pl.isLightBulbOn=False;r['cradlePadAddedVolumeMm3']=cb.volume*1000-before;save()
  # Lightweight view references: source meshes, not falsely described as native analytic board solids.
  for ref in cfg['references']:
   same=[o for o in root.occurrences if o.component.name==ref['name']];assert len(same)<=1
   if same:continue
   o=root.occurrences.addNewComponent(matrix(ref.get('worldTransform',[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])));o.component.name=ref['name'];base=o.component.features.baseFeatures.add();base.startEdit()
   try:meshes=o.component.meshBodies.add(ref['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert meshes.count>=1
   finally:base.finishEdit()
   o.component.attributes.add('MicroDuck','source',json.dumps(ref));save()
  afterbox=bbox(cap);r['finalBoundsMm']=afterbox;r['finalSolid']=cap.isSolid;r['finalVolumeMm3']=cap.volume*1000;r['noGlobalExpansion']=all(afterbox[0][i]>=r['beforeBoundsMm'][0][i]-1e-4 and afterbox[1][i]<=r['beforeBoundsMm'][1][i]+1e-4 for i in range(3));assert r['noGlobalExpansion']
  files=[];arc=OUT/'MicroDuck-closed-head-Pi-audio-mounts.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(arc)));files.append(arc)
  step=OUT/'closed-cap-Pi-audio-mounts.step';assert design.exportManager.execute(design.exportManager.createSTEPExportOptions(str(step),comp));files.append(step)
  stl=OUT/'closed-cap-Pi-audio-mounts-world.stl';o=design.exportManager.createSTLExportOptions(cap,str(stl));o.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh;assert design.exportManager.execute(o);files.append(stl)
  for ext in ['step','stl']:
   path=OUT/('speaker-cradle-single-seat-adjustment.'+ext)
   op=design.exportManager.createSTEPExportOptions(str(path),cc) if ext=='step' else design.exportManager.createSTLExportOptions(cb,str(path))
   if ext=='stl':op.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
   assert design.exportManager.execute(op);files.append(path)
  r['referenceCount']=len(cfg['references']);r['cradleFinalSolid']=cb.isSolid
  r.update(status='NATIVE_AUDIO_FEATURES_CREATED_NEIGHBOR_CHECK_PENDING',exports=[{'file':str(p),'sha256':sha(p)}for p in files],elapsedSeconds=time.time()-t0,notes=cfg['notes']);save()
 except Exception:r.update(status='FAILED_NOT_RELEASED',error=traceback.format_exc(),elapsedSeconds=time.time()-t0);save();raise
run()
