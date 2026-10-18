from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;N=D.parent
exec((N/'build_body_routes.py').read_text().split('rows=[]')[0].replace('D=Path(__file__).resolve().parent','D=Path(__file__).resolve().parent'))
rows=[]
for net,y0,y,jy in [('5v',-10.5,-7.6,-7),('gnd',.2,-3.8,7)]:
 ps=[[-30.85,y0,0],[-30.85,y0,3],[-33.5,y,17],[-33.5,y,37.4],[-21,y,37.4],[-15,jy,35.5],[-1,jy,35.5]]
 if net=='gnd':ps=ps[:4]+[[-16,y,37.4],[-8,jy,35.5],[-1,jy,35.5]]
 path,sections=fillet_path(ps,6)
 # Bare lead through the same exposed rear solder land. Insulation starts 0.8 mm after the board-facing transition.
 def edge(s):return cq.Edge.makeLine(vec(s['start']),vec(s['end'])) if s['type']=='line' else cq.Edge.makeThreePointArc(vec(s['start']),vec(s['mid']),vec(s['end']))
 es=[edge(s) for s in sections];s=sections[2];split=add(s['start'],mul(unit(sub(s['end'],s['start'])),.8))
 bare=cq.Wire.assembleEdges(es[:2]+[cq.Edge.makeLine(vec(s['start']),vec(split))]);body=cq.Wire.assembleEdges([cq.Edge.makeLine(vec(split),vec(s['end']))]+es[3:])
 for name,p,start,axis,r in [('pad',bare,ps[0],[0,0,1],.65),('insulated',body,split,sub(s['end'],s['start']),1.6)]:
  q=cq.Workplane(cq.Plane(origin=vec(start),normal=vec(axis))).circle(r).sweep(cq.Workplane('XY').newObject([p]),isFrenet=False).val()
  if name=='pad':q=q.fuse(cq.Solid.makeCylinder(1,1.3,vec([-31.5,y0,0]),vec([1,0,0])))
  assert q.isValid() and len(q.Solids())==1
  key=f'distribution_{net}_{name}';file=D/(key+'-world.stl');step=D/(key+'-world.step');cq.exporters.export(q,str(file),tolerance=.01,angularTolerance=.1);cq.exporters.export(q,str(step))
  rows.append({'key':key,'net':net.upper(),'file':str(file),'nativeStep':str(step),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'lengthMm':p.Length(),'diameterMm':2*r,'minimumBendRadiusMm':6,'start':start,'end':split if name=='pad' else ps[-1],'splitPlane':split,'splitAxis':unit(sub(s['end'],s['start'])),'junctionReceivingKey':f'distribution_{net}'})
(D/'distribution-feeds.json').write_text(json.dumps({'parts':rows,'polylinesDesign':{'note':'Filleted source path, not straight segment artwork'},'gauge':'16 AWG engineering requirement, actual wire stock insulation must fit 3.2 mm receiving envelope','jointStatus':'Insulated splice receiving geometry is not certification of a physical solder/crimp joint','sourceHashes':{str(N/'build_body_routes.py'):hashlib.sha256((N/'build_body_routes.py').read_bytes()).hexdigest(),str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'wholeHarnessAccepted':False},indent=2)+'\n')
print([(x['key'],x['lengthMm']) for x in rows])
