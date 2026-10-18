import adsk.core,adsk.fusion,json,hashlib,traceback
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/head-layout');O=D/'audio-relocation/native'
def p(x,y,z):return adsk.core.Point3D.create(x/10,y/10,z/10)
r={}
try:
 app=adsk.core.Application.get();doc=next(d for d in app.documents if d.name=='MicroDuck Pi roof mounts native study');doc.activate();des=adsk.fusion.Design.cast(app.activeProduct);root=des.rootComponent
 palette={}
 for name,rgb in [('shell',(234,207,64)),('pcb',(23,97,74)),('hardware',(83,89,96)),('speaker',(49,50,53)),('inner',(217,164,46))]:
  a=des.appearances.itemByName('MicroDuck '+name)
  if not a:a=des.appearances.add('MicroDuck '+name)
  a.color=adsk.core.Color.create(*rgb,255);palette[name]=a
 for occ in root.occurrences:
  n=occ.component.name.lower()
  if 'exact original' in n:occ.isLightBulbOn=False;continue
  occ.isLightBulbOn=True
  key='shell'if 'closed cap' in n or 'head_bottom'in n or 'face_panel'in n else 'pcb'if 'reference pi' in n or 'amplifier' in n or 'camera_board' in n else 'speaker'if 'speaker' in n else 'hardware'
  for b in occ.component.bRepBodies:b.appearance=palette[key]
  for b in occ.component.meshBodies:b.appearance=palette[key]
 def shot(name,eye,target,up):
  cam=app.activeViewport.camera;cam.eye=p(*eye);cam.target=p(*target);cam.upVector=adsk.core.Vector3D.create(*up);cam.isFitView=False;cam.viewExtents=18;cam.isSmoothTransition=False;app.activeViewport.camera=cam;app.activeViewport.refresh();q=O/name;assert app.activeViewport.saveAsImageFile(str(q),1440,1000);return str(q)
 r['exterior']=shot('closed-head-exterior-native.png',[-150,-175,240],[30,0,132],[0,0,1])
 for occ in root.occurrences:
  if occ.component.name.startswith('REFERENCE fixed head'):occ.isLightBulbOn=False
 r['underside']=shot('head-mounts-underside-native.png',[0,-120,35],[30,0,140],[0,0,1]);r['scope']='Rigid head mount layout; complete flexible harness and body-controller architecture not accepted.'
except Exception:r['error']=traceback.format_exc()
(O/'native-views.json').write_text(json.dumps(r,indent=2))
