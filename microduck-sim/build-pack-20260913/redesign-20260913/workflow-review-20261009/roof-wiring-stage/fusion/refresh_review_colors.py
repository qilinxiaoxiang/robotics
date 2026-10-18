import adsk.core,adsk.fusion,json,hashlib,time,traceback
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/roof-wiring-stage/fusion')
app=adsk.core.Application.get()
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

d=json.loads((P/'fusion-import-manifest.json').read_text());bykey={p['key']:p for p in d['parts']};design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;colors={};seen=[]
for o in root.occurrences:
 for b in o.component.meshBodies:
  key=b.name.split(' - ')[0];p=bykey[key];c=p['color']
  if c not in colors:
   a=design.appearances.add('Review '+c);a.color=adsk.core.Color.create(*[int(c[i:i+2],16) for i in (1,3,5)],255);a.roughness=.65;colors[c]=a
  b.appearance=colors[c];bb=bounds(b,o);err=max(abs(bb[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3));assert err<.002;seen.append(key)
assert set(seen)==set(bykey)
capture('head-closed.png',(28,32,31),(2.5,0,13),15,root,head=True)
capture('head-wires.png',(-28,-32,35),(2.5,0,13),16,root,head=True,opened=True,ghost=True)
capture('whole-wiring.png',(-48,55,28),(0,0,0),39,root,ghost=True)
capture('whole-closed.png',(48,55,35),(0,0,0),39,root)
archive=P/'MicroDuck-roof-and-wiring-stage.f3d';assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
old=app.activeDocument;readDoc=app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(str(archive)));readDoc.name='MicroDuck - restored roof and routed wiring - stage review';rd=adsk.fusion.Design.cast(app.activeProduct);readback=[]
for o in rd.rootComponent.occurrences:
 for b in o.component.meshBodies:
  key=b.name.split(' - ')[0];p=bykey[key];bb=bounds(b,o);err=max(abs(bb[i][j]-p['expectedFinalBoundsMm'][i][j]) for i in range(2) for j in range(3));assert err<.002;readback.append({'key':key,'maxErrorMm':err})
assert len(readback)==len(bykey)
capture('head-closed-readback.png',(28,32,31),(2.5,0,13),15,rd.rootComponent,head=True)
capture('whole-closed-readback.png',(48,55,35),(0,0,0),39,rd.rootComponent)
r=json.loads((P/'fusion-receipt.json').read_text());r.update(manifestSha256=hashlib.sha256((P/'fusion-import-manifest.json').read_bytes()).hexdigest(),archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),readback=readback,reviewColorsApplied=True);(P/'fusion-receipt.json').write_text(json.dumps(r,indent=2)+'\n');old.close(False)
