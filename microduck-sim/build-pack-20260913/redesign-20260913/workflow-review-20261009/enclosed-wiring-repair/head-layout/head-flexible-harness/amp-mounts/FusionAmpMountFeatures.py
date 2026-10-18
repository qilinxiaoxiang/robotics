"""Increment the owning native cap; call add_amp_mounts(comp, cap, original_stop).
comp/cap coordinates must already be world mm expressed in Fusion centimetres.
original_stop is the original closed cap BRep in the same assembly context.
No import, document switch, exterior cut or replacement of other mounts.
"""
import adsk.core,adsk.fusion,json
from pathlib import Path
SPEC=Path(__file__).with_name('amp-mount-fragment.json')
def add_amp_mounts(comp,cap,original_stop):
 cfg=json.loads(SPEC.read_text());assert cfg['integrationReady'];created=[]
 for i,spec in enumerate(cfg['mounts']):
  for kind in ['boss','pilot']:
   name=f'Current amp mount {i} {kind}'
   existing=[x for x in comp.features.extrudeFeatures if x.name==name]
   if existing:continue
   z=spec['seatZMm'];plane=comp.constructionPlanes.createInput();plane.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(z/10));pl=comp.constructionPlanes.add(plane);sk=comp.sketches.add(pl);sk.name=name
   x,y=spec['xyMm'];r=(spec['bossDiameterMm']if kind=='boss'else spec['pilotDiameterMm'])/20
   sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(x/10,y/10,0),r);assert sk.profiles.count==1
   operation=adsk.fusion.FeatureOperations.JoinFeatureOperation if kind=='boss'else adsk.fusion.FeatureOperations.CutFeatureOperation
   ex=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),operation)
   extent=adsk.fusion.ToEntityExtentDefinition.create(original_stop,True)if kind=='boss'else adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(spec['pilotDepthMm']/10))
   ex.setOneSideExtent(extent,adsk.fusion.ExtentDirections.PositiveExtentDirection);ex.participantBodies=[cap];feature=comp.features.extrudeFeatures.add(ex);feature.name=name;sk.isVisible=False;pl.isLightBulbOn=False;assert cap.isSolid;created.append({'name':name,'token':feature.entityToken})
 return created
