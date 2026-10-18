"""Run in Autodesk Fusion. Separate reversible native part revision; no UI automation.
Original meshes remain faceted BReps. Only the new sketch/extrusions are native features.
"""
import adsk.core,adsk.fusion,json,math,hashlib,traceback,time
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/body-partition/native-usb-passage')
SPEC=D/'passage-spec.json';RECEIPT=D/'fusion-passage-receipt.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def matrix(t):
 a=[v for row in t for v in row]
 for i in [3,7,11]:a[i]/=10
 m=adsk.core.Matrix3D.create();assert m.setWithArray(a);return m
def bounds(b):return [[10*v for v in b.boundingBox.minPoint.asArray()],[10*v for v in b.boundingBox.maxPoint.asArray()]]
def point(x,y):return adsk.core.Point3D.create(x/10,y/10,0)
def run(context=None):
 start=time.time();r={'status':'RUNNING','printReady':False,'wholeRobotAccepted':False,'physicalStrengthVerified':False,'specSha256':sha(SPEC),'scriptSha256':sha(D/'FusionBodyUsbNotch.py'),'parts':[],'nativeInterferenceQueries':0,'exports':[]}
 def save():RECEIPT.write_text(json.dumps(r,indent=2)+'\n')
 try:
  cfg=json.loads(SPEC.read_text())
  for p,v in cfg['sourceHashes'].items():assert sha(p)==v,('Changed source',p)
  for x in cfg['shells']+cfg['plugReferences']+[cfg['openrbReference']]:assert sha(x['file'])==x['sha256'],x['file']
  app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='MicroDuck body USB U-notch - native local revision';design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;root=design.rootComponent
  design.userParameters.add('usbPassageStart',adsk.core.ValueInput.createByString('37 mm'),'mm','Existing upper shell passage start')
  design.userParameters.add('usbPassageDepth',adsk.core.ValueInput.createByString('7 mm'),'mm','Cut through upper skins only')
  r['documentName']=doc.name;save()
  def newcomp(name,t=None):
   occ=root.occurrences.addNewComponent(matrix(t)if t else adsk.core.Matrix3D.create());occ.component.name=name;return occ
  def mesh_native(meta,name):
   tr=meta.get('worldTranslationMm',[0,0,0]);t=[[1,0,0,tr[0]],[0,1,0,tr[1]],[0,0,1,tr[2]],[0,0,0,1]];occ=newcomp(name,t);comp=occ.component;base=comp.features.baseFeatures.add();base.startEdit()
   try:ms=comp.meshBodies.add(meta['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base);assert ms.count==1
   finally:base.finishEdit()
   inp=comp.features.meshConvertFeatures.createInput([comp.meshBodies.item(0)]);inp.meshConvertMethodType=adsk.fusion.MeshConvertMethodTypes.FacetedMeshConvertMethodType;assert comp.features.meshConvertFeatures.add(inp)
   assert comp.bRepBodies.count==1;body=comp.bRepBodies.item(0);assert body.isSolid and body.volume>0
   for i in range(comp.meshBodies.count):comp.meshBodies.item(i).isLightBulbOn=False
   comp.attributes.add('MicroDuck','source',json.dumps(meta));return occ,body
  def worldbody(body,occ):return body.createForAssemblyContext(occ)
  def interference(a,b):
   ab=bounds(a);bb=bounds(b)
   if any(ab[1][i]<bb[0][i]or bb[1][i]<ab[0][i]for i in range(3)):return 0.
   c=adsk.core.ObjectCollection.create();c.add(a);c.add(b);inp=design.createInterferenceInput(c);inp.areCoincidentFacesIncluded=False;res=design.analyzeInterference(inp);assert res is not None;r['nativeInterferenceQueries']+=1
   return sum(res.item(i).interferenceBody.volume*1000 for i in range(res.count))
  def plane(comp,z):
   x=comp.constructionPlanes.createInput();x.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByString('usbPassageStart' if z==cfg['opening']['zStartMm'] else str(z)+' mm'));return comp.constructionPlanes.add(x)
  def notch_profile(comp,name):
   spec=cfg['opening'];x0=spec['xRearMm'];x1=spec['xFrontMm'];y0=spec['yMinMm'];y1=spec['yMaxMm'];rad=spec['rearCornerRadiusMm'];pl=plane(comp,spec['zStartMm']);sk=comp.sketches.add(pl);sk.name=name+' - rear R2 U-notch into existing opening';lines=sk.sketchCurves.sketchLines;arcs=sk.sketchCurves.sketchArcs
   lines.addByTwoPoints(point(x0+rad,y0),point(x1,y0));lines.addByTwoPoints(point(x1,y0),point(x1,y1));lines.addByTwoPoints(point(x1,y1),point(x0+rad,y1));arcs.addByCenterStartSweep(point(x0+rad,y1-rad),point(x0+rad,y1),math.pi/2);lines.addByTwoPoints(point(x0,y1-rad),point(x0,y0+rad));arcs.addByCenterStartSweep(point(x0+rad,y0+rad),point(x0,y0+rad),math.pi/2)
   assert sk.profiles.count==1,('Expected one notch profile',sk.profiles.count);pl.isLightBulbOn=False;return sk
  shell_objects=[]
  for meta in cfg['shells']:
   assert meta['worldCoordinatesAlreadyApplied'] and meta['importTranslationMm']==[0,0,0], 'Avoid applying source ID8/10 world transform twice'
   occ,b=mesh_native(meta,meta['key']+' - revised USB passage');shell_objects.append((meta,occ,b))
  # Exact manufacturer BReps as independent reference bodies; no consolidation.
  rb=cfg['openrbReference'];rbocc=newcomp('REFERENCE - OpenRB manufacturer assembly',rb['nativeToWorld']);assert app.importManager.importToTarget(app.importManager.createSTEPImportOptions(rb['file']),rbocc.component)
  rbrefs=[rbocc.bRepBodies.item(i)for i in range(rbocc.bRepBodies.count)]
  for i in range(root.allOccurrences.count):
   o=root.allOccurrences.item(i)
   if o.fullPathName.startswith(rbocc.fullPathName+'+')or o.fullPathName.startswith(rbocc.fullPathName+'/'):
    rbrefs.extend(o.bRepBodies.item(j)for j in range(o.bRepBodies.count))
  assert len(rbrefs)>100,('OpenRB reference solid count',len(rbrefs));r['manufacturerReferenceBodies']=len(rbrefs)
  plugs=[]
  for meta in cfg['plugReferences']:
   o,b=mesh_native(meta,'REFERENCE - '+meta['key']);plugs.append((meta['key'],worldbody(b,o)))
  refs=rbrefs+[b for _,b in plugs]
  for meta,occ,body in shell_objects:
   comp=occ.component;before=body.volume*1000;before_bounds=bounds(body);entry={'key':meta['key'],'sourceSha256':meta['sha256'],'sourceCommunityId':meta['originalCommunitySourceId'],'beforeVolumeMm3':before,'beforeBoundsMm':before_bounds,'originalPlugIntersectionsMm3':{k:interference(worldbody(body,occ),b)for k,b in plugs},'rails':[]};r['parts'].append(entry);save()
   sk=notch_profile(comp,meta['key']);ex=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.CutFeatureOperation);ex.setDistanceExtent(False,adsk.core.ValueInput.createByString('usbPassageDepth'));ex.participantBodies=[body];cut=comp.features.extrudeFeatures.add(ex);assert cut;cut.name='USB U-notch through existing upper opening';sk.isVisible=False
   assert comp.bRepBodies.count==1;body=comp.bRepBodies.item(0);assert body.isSolid and body.volume>0;cutvolume=before-body.volume*1000;assert cutvolume>0;entry['cutVolumeMm3']=cutvolume;entry['afterCutVolumeMm3']=body.volume*1000;save()
   for index,rail in enumerate(meta['rails']):
    rr={'index':index,'sourceRoofEnvelope':rail,'added':False};entry['rails'].append(rr)
    if not rail['eligibleRoofEnvelope']:rr['reason']='Source roof projection does not prove internal envelope';continue
    origin=rail['originMm'];dims=rail['sizeMm'];pl=plane(comp,origin[2]);rs=comp.sketches.add(pl);rs.name='Independent inner2mm rail '+str(index);rs.sketchCurves.sketchLines.addTwoPointRectangle(point(origin[0],origin[1]),point(origin[0]+dims[0],origin[1]+dims[1]));re=comp.features.extrudeFeatures.addSimple(rs.profiles.item(0),adsk.core.ValueInput.createByReal(dims[2]/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);railbody=re.bodies.item(0);rp=worldbody(railbody,occ);attachment=interference(rp,worldbody(body,occ));contacts=[{'reference':x.name,'volumeMm3':v}for x in refs if (v:=interference(rp,x))>1e-7];rr.update(attachmentOverlapMm3=attachment,referenceContacts=contacts)
    if attachment<=1e-7 or contacts:
     rr['reason']='No native attachment or reference collision';re.deleteMe();rs.isVisible=False;pl.isLightBulbOn=False;continue
    tools=adsk.core.ObjectCollection.create();tools.add(railbody);ci=comp.features.combineFeatures.createInput(body,tools);ci.operation=adsk.fusion.FeatureOperations.JoinFeatureOperation;ci.isKeepToolBodies=False;joined=comp.features.combineFeatures.add(ci);assert joined;joined.name='Inner rail joined only to '+meta['key'];assert comp.bRepBodies.count==1;body=comp.bRepBodies.item(0);rr['added']=True;rr['reason']='Native connected solid; references clear; original upper roof envelope retained';rs.isVisible=False;pl.isLightBulbOn=False;save()
   entry['finalVolumeMm3']=body.volume*1000;entry['addedRailVolumeMm3']=entry['finalVolumeMm3']-entry['afterCutVolumeMm3'];entry['finalBoundsMm']=bounds(body);entry['finalSolid']=body.isSolid;entry['finalPlugIntersectionsMm3']={k:interference(worldbody(body,occ),b)for k,b in plugs}
   assert all(v<1e-7 for v in entry['finalPlugIntersectionsMm3'].values()),entry['finalPlugIntersectionsMm3'];assert max(abs(entry['finalBoundsMm'][i][j]-before_bounds[i][j])for i in [0,1]for j in range(3))<1e-4,'Unexpected overall shell size change'
   step=D/(meta['key']+'-usb-u-notch.step');opts=design.exportManager.createSTEPExportOptions(str(step),comp);assert design.exportManager.execute(opts)
   f3d=D/(meta['key']+'-usb-u-notch.f3d');opts=design.exportManager.createFusionArchiveExportOptions(str(f3d));opts.geometry=occ;assert design.exportManager.execute(opts)
   for p in [step,f3d]:r['exports'].append({'file':str(p),'sha256':sha(p),'key':meta['key']})
   save();adsk.doEvents()
  archive=D/'body-usb-u-notch-with-board-references.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)));r['exports'].append({'file':str(archive),'sha256':sha(archive),'role':'Local reference assembly only, no full head or whole robot acceptance'})
  r.update(status='LOCAL_NATIVE_NOTCH_AND_PLUG_CHECK_PASSED',localGeometryPassed=True,elapsedSeconds=round(time.time()-start,2),limitations=['Source shells are faceted BReps, not recovered original analytical feature history.','Cut removes original0.89–1.02mm bridge into existing opening; no front reinforcement bridge is created.','Rear/side rail results are geometric only, not physical strength or fatigue verification.','DFR relocation, mounting, wiring and full robot motion remain separate.','USB7mm mould thickness and1.2mm shoulder standoff are receiving assumptions, not measured cable dimensions.']);save()
 except Exception:r.update(status='FAILED_NOT_RELEASED',error=traceback.format_exc(),elapsedSeconds=round(time.time()-start,2));save();raise

run(None)
