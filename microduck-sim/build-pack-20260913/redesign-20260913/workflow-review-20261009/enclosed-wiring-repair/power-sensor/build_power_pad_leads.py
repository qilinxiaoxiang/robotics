from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
# Reuse only pure path definitions; the historical mixed generator must not rewrite frozen IMU assets.
exec((D/'build_body_routes.py').read_text().split('rows=[]')[0])
rows=[]
for net,y0,y1 in [('5V',-10.5,-7.6),('GND',.2,-3.8)]:
 points=[[-30.85,y0,0],[-30.85,y0,3],[-33.5,y1,17],[-33.5,y1,37.4],[-12,y1,37.4],[6,y1,48],[6,y1,55]]
 path,segs=fillet_path(points,6);es=path.Edges()
 # Build ordered edges from recorded sections rather than relying on topology order.
 def edge(s):return cq.Edge.makeLine(vec(s['start']),vec(s['end'])) if s['type']=='line' else cq.Edge.makeThreePointArc(vec(s['start']),vec(s['mid']),vec(s['end']))
 e=[edge(s) for s in segs];s=segs[2];cut=add(s['start'],mul(unit(sub(s['end'],s['start'])),.8))
 barepath=cq.Wire.assembleEdges(e[:2]+[cq.Edge.makeLine(vec(s['start']),vec(cut))]);mainpath=cq.Wire.assembleEdges([cq.Edge.makeLine(vec(cut),vec(s['end']))]+e[3:])
 for suffix,wire,start,axis,radius in [('pad-lead',barepath,points[0],[0,0,1],.65),('pad-connected',mainpath,cut,sub(s['end'],s['start']),1.6)]:
  shape=cq.Workplane(cq.Plane(origin=vec(start),normal=vec(axis))).circle(radius).sweep(cq.Workplane('XY').newObject([wire]),isFrenet=False).val()
  if suffix=='pad-lead':
   solder=cq.Solid.makeCylinder(1.,1.3,vec([-31.5,y0,0]),vec([1,0,0]));shape=shape.fuse(solder)
  assert shape.isValid() and len(shape.Solids())==1
  key='power_'+net.lower()+'_'+suffix.replace('-','_');stl=D/(key+'-world.stl');step=D/(key+'-world.step');cq.exporters.export(shape,str(step));cq.exporters.export(shape,str(stl),tolerance=.01,angularTolerance=.1)
  rows.append({'key':key,'net':net,'file':str(stl),'nativeStep':str(step),'sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'lengthMm':wire.Length(),'diameterMm':2*radius,'minimumBendRadiusMm':6,'solderAttachmentRegionMm':[[-31.5,y0-1,-1],[-30.2,y0+1,1]] if suffix=='pad-lead' else None,'start':start,'end':cut if suffix=='pad-lead' else points[-1],'routeSections':(segs[:2]+[dict(segs[2],end=cut)]) if suffix=='pad-lead' else ([dict(segs[2],start=cut)]+segs[3:]),'pathSplitWorldMm':cut})
(D/'power-pad-routes.json').write_text(json.dumps({'parts':rows,'boardDatum':'PCB rear face placed at existing receiving-envelope back plane X=-31.5; pads use actual exposed back gold land at top edge. This is an explicit installation datum, not a measured PCB-thickness claim.','padCentersYmm':{'VOUT':-10.5,'GND':.2},'padCentersSourceUncertaintyMm':.8,'solderFillet':'Radius1mm and1.3mm outward projection are an assembly receiving design, not a manufacturer solder-joint specification.','wholeElectricalConnectionAccepted':False},indent=2)+'\n');print([(r['key'],r['lengthMm'],r['pathSplitWorldMm']) for r in rows])
