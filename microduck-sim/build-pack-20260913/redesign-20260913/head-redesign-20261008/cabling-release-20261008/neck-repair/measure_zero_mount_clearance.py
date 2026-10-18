"""Read official vector drawing; no CAD or inferred manufacturer keepout claim."""
from zero_vector_paths import paths,P,dist
import hashlib,json,math
allp={p['id']:p for p in paths}
holes=[('drawing-top-left',472,439),('drawing-top-right',421,422),('drawing-bottom-left',440,435),('drawing-bottom-right',308,309)]
exclude={k for _,a,b in holes for k in [a,b]}
# SVG zero-based path922 starts PCB perimeter; later paths are dimensions/text.
components=[p for p in paths if p['id']<922 and p['id'] not in exclude]
scale=(allp[929]['bbox'][0]-allp[923]['bbox'][0])/65
rows=[]
for name,inner,outer in holes:
 box=allp[inner]['bbox'];center=[(box[0]+box[2])/2,(box[1]+box[3])/2]
 near=sorted((min(dist(center,*s) for s in p['segments']),p['id']) for p in components)[:8]
 distance,pid=near[0];p=allp[pid]
 # Half drawn stroke is conservatively counted inward; 0.05mm combines SVG flattening/registration, not part tolerance.
 outline_clear=(distance-p['width']/2)/scale
 usable=outline_clear-.05
 rows.append({'hole':name,'centerSvgPt':center,'holeCirclePathIndex':inner,'surroundingUndimensionedCirclePathIndex':outer,'nearestComponentContourPathIndex':pid,'nearestContourSvgBounds':p['bbox'],'nearestContourDistanceMm':distance/scale,'distanceIncludingHalfStrokeMm':outline_clear,'drawingInferenceAllowanceMm':.05,'conservativeDrawingOnlyRadiusMm':usable,'proposedToolVoidRadiusMm':2.2,'remainingDrawingClearanceAfterRadius2_2Mm':usable-2.2,'driverDiameter3MmPasses2D':usable>=1.5,'screwHeadDiameter4MmPlusRadial0_2Passes2D':usable>=2.2,'nearestEightComponentPaths':[{'pathIndex':i,'distanceMm':d/scale} for d,i in near]})
report={'accepted3DHardwareFit':False,'purpose':'Evidence supporting removal of an overly conservative component-box volume near existing mounting holes; actual geometry remains an obstacle.','verificationDate':'2026-10-08','primarySourceUrl':'https://pip-assets.raspberrypi.com/categories/592-raspberry-pi-zero-w/documents/RP-008367-DS-1-raspberry-pi-zero-w-mechanical-drawing.pdf','drawing':'Raspberry Pi Zero W mechanical drawing RP-008367-DS-1','declaredPCBSizeMm':[65,30],'declaredMountingPitchMm':[58,23],'svgPointsPerMm':scale,'pathSelection':{'components':'zero-based SVG path indices0..921, excluding eight mounting inner/outer circles','pcbAndDimensions':'922..1146 excluded; PCB edge/holes retained separately in physical verifier'},'proposedComponentBoxVoidRadiusMm':2.2,'rows':rows,'limitations':['The drawing does not state a manufacturer mounting keepout diameter or component position/height tolerance. Radius2.2 is a conservative design inference, not a guaranteed vendor keepout.','Only subtract these cylinders from the conservative zero_w_components receiving box. Do not remove PCB material, actual connector/header/component bodies, solder tails, chassis, or actual hardware.','This 2D drawing cannot certify a45mm driver corridor through the assembled robot; rerun all actual surrounding obstacles.','Screw-head axial seating, washer thickness, PCB underside protrusions and driver access are separate checks.','The larger concentric hole circles are not dimensioned; they were not treated as a specified component keepout.'],'sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'zero-w-official-mechanical.pdf',P/'zero-w-official-mechanical.svg',P/'zero_vector_paths.py',P/'measure_zero_mount_clearance.py']}}
assert all(r['conservativeDrawingOnlyRadiusMm']>2.2 for r in rows)
(P/'zero-w-mount-clearance-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'svgPointsPerMm':scale,'rows':rows,'reportSha256':hashlib.sha256((P/'zero-w-mount-clearance-evidence.json').read_bytes()).hexdigest()},indent=2))
