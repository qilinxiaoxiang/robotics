"""Run in Fusion. Creates a NEW local review document, never edits the active robot.
Native manufacturer motor solids + unchanged local mesh references + editable
line/arc 3D sketches and solid sweeps. This is NOT a completed harness release.
"""
import adsk.core, adsk.fusion
from pathlib import Path
import json, hashlib, traceback, math
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires')
ROUTE_FILE='local-route.json' # mirror-route.json is the independently checked 8 -> 9 station

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(v):return adsk.core.Point3D.create(*[x/10 for x in v])
def transform(T):
 m=adsk.core.Matrix3D.create();a=[v for row in T for v in row]
 for i in [3,7,11]:a[i]/=10
 m.setWithArray(a);return m

def run(context):
 report={'status':'RUNNING','wholeHarnessAccepted':False,'routeFile':str(D/ROUTE_FILE),'routeSha256':sha(D/ROUTE_FILE),'constraints':[],'curves':[],'sweeps':[]}
 try:
  cfg=json.loads((D/ROUTE_FILE).read_text());assert cfg['allStaticClear']
  for p,h in cfg['sourceHashes'].items():assert sha(p)==h, p
  app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
  design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType
  root=design.rootComponent
  doc.name='LOCAL '+cfg['route']+' 180mm route REVIEW'
  report['documentName']=doc.name
  def component(name,T=None):
   occ=root.occurrences.addNewComponent(transform(T) if T else adsk.core.Matrix3D.create());occ.component.name=name;return occ
  # Manufacturer solids are already registered to guide motor-local coordinates.
  manufacturer=D.parents[1]/'leg-ports/xl330-registered-motor-local.step'
  report['manufacturerStep']={'file':str(manufacturer),'sha256':sha(manufacturer)}
  for end in ['source','target']:
   port=cfg['strands'][0][end];occ=component('XL330 native ID'+str(port['motor']),port['transform'])
   opts=app.importManager.createSTEPImportOptions(str(manufacturer));assert app.importManager.importToTarget(opts,occ.component)
   # Registered mouth and outgoing axis stay editable, and are visually distinct construction geometry.
   ref=root.sketches.add(root.xYConstructionPlane);ref.name=f"ID{port['motor']} registered socket axis"
   mouth=port['mouth'];endpt=[mouth[i]+8*port['outward'][i] for i in range(3)]
   axis=ref.sketchCurves.sketchLines.addByTwoPoints(point(mouth),point(endpt));axis.isConstruction=True
   ref.attributes.add('MicroDuck','portEvidence','Manufacturer header surface registration; no pin-order inference')
   # Full catalogue receiving envelope; explicit intended own-header mating, not detailed female CAD.
   hp=component(f"ID{port['motor']} EHR3 receiving envelope",port['transform']);c=hp.component;lo,hi=port['housingLocalBounds']
   pi=c.constructionPlanes.createInput();pi.setByOffset(c.xYConstructionPlane,adsk.core.ValueInput.createByReal(lo[2]/10));pl=c.constructionPlanes.add(pi)
   sk=c.sketches.add(pl);sk.name='Catalog bounding profile; detailed latch not modeled'
   sk.sketchCurves.sketchLines.addTwoPointRectangle(point([lo[0],lo[1],0]),point([hi[0],hi[1],0]))
   ext=c.features.extrudeFeatures.addSimple(sk.profiles.item(0),adsk.core.ValueInput.createByReal((hi[2]-lo[2])/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
   ext.bodies.item(0).name='EHR3 catalogue receiving solid; mate overlap not acceptance';sk.isVisible=False
  OLD=D.parents[1]/'roof-wiring-stage/motor-wires'
  # Import only actual AABB-near printed/ring obstacles. They remain meshes: not silently BRep-certified.
  keys=sorted({c['key']for r in cfg['strands']for c in r['checked']if not c['key'].startswith('motor')})
  report['meshReferences']=[]
  for key in keys:
   meta=json.loads((OLD/'obstacles'/f'{key}.json').read_text());assert sha(meta['file'])==meta['sha256']
   T=[[1,0,0,meta.get('importTranslationMm',[0,0,0])[0]],[0,1,0,meta.get('importTranslationMm',[0,0,0])[1]],[0,0,1,meta.get('importTranslationMm',[0,0,0])[2]],[0,0,0,1]]
   occ=component('SOURCE MESH '+key,T)
   base=occ.component.features.baseFeatures.add();base.name='Unchanged source mesh '+key;base.startEdit()
   try:bodies=occ.component.meshBodies.add(meta['file'],adsk.fusion.MeshUnits.MillimeterMeshUnit,base)
   finally:base.finishEdit()
   for i in range(bodies.count):bodies.item(i).name=key+' unchanged source reference'
   occ.component.opacity=.35;report['meshReferences'].append({'key':key,'sourceSha256':meta['sha256'],'nativeBRepInterferenceCovered':False,'meshCheckCovered':True})
  for row in cfg['strands']:
   occ=component('Conductor '+str(row['id'])+' 180mm');comp=occ.component
   sk=comp.sketches.add(comp.xYConstructionPlane);sk.name='EDITABLE 3D route; local R2 and storage R4'
   curves=[]
   for i,p in enumerate(row['primitives']):
    if p['kind']=='line':c=sk.sketchCurves.sketchLines.addByTwoPoints(point(p['start']),point(p['end']))
    else:c=sk.sketchCurves.sketchArcs.addByThreePoints(point(p['start']),point(p['mid']),point(p['end']))
    assert c;c.attributes.add('MicroDuck','primitive',json.dumps(p));curves.append(c)
   # Constraint failures remain visible in the receipt; never substitute a hidden fitted spline.
   for i,(a,b) in enumerate(zip(curves,curves[1:])):
    try:sk.geometricConstraints.addTangent(a,b);report['constraints'].append({'wire':row['id'],'join':i,'tangentConstraint':True})
    except Exception as e:report['constraints'].append({'wire':row['id'],'join':i,'tangentConstraint':False,'reason':str(e),'analyticTangencyMustPass':True})
   for p,c in zip(row['primitives'],curves):
    if p['kind']=='arc':
     try:
      dim=sk.sketchDimensions.addRadialDimension(c,point(p['mid']),False)
      dim.attributes.add('MicroDuck','radiusScope','Receiving design radius; not manufacturer minimum')
     except Exception as e:report['constraints'].append({'wire':row['id'],'radialAnnotation':False,'reason':str(e)})
   # Confirm native creation/solver preserved the exact checked line/arc path.
   total=0.
   for p,c in zip(row['primitives'],curves):
    g=c.worldGeometry;a=g.startPoint;b=g.endPoint
    err=min(max(a.distanceTo(point(p['start'])),b.distanceTo(point(p['end']))),max(a.distanceTo(point(p['end'])),b.distanceTo(point(p['start']))))*10
    assert err<1e-5,('Native curve endpoint changed',err)
    if p['kind']=='arc':assert abs(g.radius*10-p['radiusMm'])<1e-5
    assert abs(c.length*10-p['lengthMm'])<1e-5
    total+=c.length*10;report['curves'].append({'wire':row['id'],'kind':p['kind'],'lengthMm':c.length*10,'endpointErrorMm':err,'radiusMm':g.radius*10 if p['kind']=='arc'else None})
   assert abs(total-180)<1e-4
   collection=adsk.core.ObjectCollection.create()
   for c in curves:collection.add(c)
   path=adsk.fusion.Path.create(collection,adsk.fusion.ChainedCurveOptions.noChainedCurves);assert path
   pi=comp.constructionPlanes.createInput()
   # Both installed API generations expose this two-argument method; newer one marks it retired.
   assert pi.setByDistanceOnPath(path,adsk.core.ValueInput.createByReal(0))
   plane=comp.constructionPlanes.add(pi);profile=comp.sketches.add(plane);profile.name='Ø1.5mm receiving diameter (not measured stock)'
   center=profile.modelToSketchSpace(point(row['primitives'][0]['start']));profile.sketchCurves.sketchCircles.addByCenterRadius(center,.075)
   inp=comp.features.sweepFeatures.createInput(profile.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
   inp.orientation=adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
   feature=comp.features.sweepFeatures.add(inp);assert feature and feature.bodies.count==1
   body=feature.bodies.item(0);assert body.isSolid and body.volume>0;body.name='Native circular sweep '+str(row['id'])
   report['sweeps'].append({'wire':row['id'],'lengthMm':total,'bodyVolumeMm3':body.volume*1000,'solid':body.isSolid,'minimumRadiusMm':2,'spareLengthModeled':True})
   profile.isVisible=False;sk.isVisible=False;plane.isLightBulbOn=False
  design.computeAll();path=D/('Fusion-'+cfg['route']+'-local-review.f3d');opts=design.exportManager.createFusionArchiveExportOptions(str(path));assert design.exportManager.execute(opts)
  report.update(status='NATIVE_CREATED_REVIEW_REQUIRED',output=str(path),outputSha256=sha(path),wholeHarnessAccepted=False,remaining=['Retention not installed/qualified','R2 and wire diameter remain explicit receiving assumptions','Insertion and joint motion not yet verified','Native positive-volume interference readback pending; meshes checked by separately bound receipt'])
  app.activeViewport.fit()
 except Exception:
  report['status']='FAILED_NOT_ACCEPTED';report['error']=traceback.format_exc()
 finally:(D/'fusion-native-readback.json').write_text(json.dumps(report,indent=2))

# The Fusion Python.Run text command executes this file directly.
run(None)
