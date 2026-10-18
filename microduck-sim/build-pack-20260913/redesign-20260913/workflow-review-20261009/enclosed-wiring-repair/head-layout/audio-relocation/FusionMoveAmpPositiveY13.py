"""Edit only the four existing amplifier circle sketches and its reference occurrence.
Native timeline rollback follows the installed Autodesk Sketch API recommendation.
No reimport/rebuild, and original failed-pose exports remain unchanged.
"""
import adsk.core,adsk.fusion,json,hashlib,traceback,time
from pathlib import Path
O=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout/audio-relocation');N=O/'positive-y13-native';N.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
r={'status':'RUNNING','wholeHeadAccepted':False,'printReady':False,'physicalFitVerified':False,'scriptSha256':sha(O/'FusionMoveAmpPositiveY13.py'),'staticCheckSha256':sha(O/'positive-y13-check.json'),'editedSketches':[]};start=time.time()
def save():(N/'native-readback.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 check=json.loads((O/'positive-y13-check.json').read_text());assert check['passed'] and check['expectedPairCount']==check['completePairCount']==89
 for row in check['inventory']:assert sha(row['file'])==row['sha256']
 app=adsk.core.Application.get();docs=[d for d in app.documents if d.name=='MicroDuck Pi roof mounts native study'];assert len(docs)==1;docs[0].activate();design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
 occ=next(o for o in root.occurrences if o.component.name=='Closed cap with integral Pi mounting bosses');comp=occ.component;assert comp.bRepBodies.count==1
 targets={'Audio amp0 boss':.6500006104,'Audio amp0 pilot':.6500006104,'Audio amp1 boss':13.3500006104,'Audio amp1 pilot':13.3500006104};sketches=[]
 for name,y in targets.items():
  matches=[s for s in comp.sketches if s.name==name];assert len(matches)==1;sketches.append((matches[0],y))
 for sk,y in sorted(sketches,key=lambda item:item[0].timelineObject.index):
  assert sk.sketchCurves.sketchCircles.count==1;circle=sk.sketchCurves.sketchCircles.item(0);c=circle.centerSketchPoint.geometry;before=[c.x*10,c.y*10,c.z*10];assert abs(before[0]-13.287000885)<1e-4;assert min(abs(before[1]-y),abs(before[1]-(y-13)))<1e-4
  if abs(before[1]-y)>1e-4:
   assert sk.timelineObject.rollTo(False);assert circle.centerSketchPoint.move(adsk.core.Vector3D.create(0,(y-before[1])/10,0))
  after=circle.centerSketchPoint.geometry;assert abs(after.y*10-y)<1e-5;r['editedSketches'].append({'name':sk.name,'beforeMm':before,'afterMm':[after.x*10,after.y*10,after.z*10]});save()
 design.timeline.moveToEnd();assert design.computeAll();assert comp.bRepBodies.count==1;cap=comp.bRepBodies.item(0);assert cap.isSolid
 for f in comp.features.extrudeFeatures:
  if f.name.startswith('Audio amp'):assert f.healthState==adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState,(f.name,f.errorOrWarningMessage)
 a=next(o for o in root.occurrences if o.component.name=='REFERENCE current relocated amplifier and X1 terminal');T=a.transform2;beforeY=T.translation.y;assert min(abs(beforeY),abs(beforeY-1.3))<1e-6
 if abs(beforeY-1.3)>1e-6:
  T.translation=adsk.core.Vector3D.create(T.translation.x,1.3,T.translation.z);a.transform2=T
 files=[]
 p=N/'MicroDuck-closed-head-Pi-audio-positive-y13.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(p)));files.append(p)
 p=N/'closed-cap-Pi-audio-positive-y13.step';assert design.exportManager.execute(design.exportManager.createSTEPExportOptions(str(p),comp));files.append(p)
 p=N/'closed-cap-Pi-audio-positive-y13-world.stl';opts=design.exportManager.createSTLExportOptions(cap,str(p));opts.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh;assert design.exportManager.execute(opts);files.append(p)
 r.update(status='NATIVE_AMP_Y13_SKETCHES_UPDATED_PENDING_DIFFERENCE_CHECK',finalCapVolumeMm3=cap.volume*1000,exports=[{'file':str(p),'sha256':sha(p)}for p in files],elapsedSeconds=time.time()-start,scope='Four existing amp sketch centers edited in timeline order; old posts are moved by their source features rather than hidden or label-filtered. Other cap/Pi/speaker/cradle features unchanged. Existing amp reference transformed once; no duplicate references.')
except Exception:r.update(status='FAILED_NATIVE_UPDATE',error=traceback.format_exc(),elapsedSeconds=time.time()-start)
finally:save()
