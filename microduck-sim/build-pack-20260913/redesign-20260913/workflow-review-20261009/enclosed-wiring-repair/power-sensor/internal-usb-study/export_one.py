from pathlib import Path
import json,sys,hashlib,cadquery as cq
D=Path(__file__).resolve().parent;cfg=json.loads((D/'candidate.json').read_text());row=next(q for q in cfg['parts']if q['key']==sys.argv[1])
if 'primitives' in row:
 pr=row['primitives'];edges=[cq.Edge.makeLine(cq.Vector(*p['start']),cq.Vector(*p['end'])) if p['kind']=='line' else cq.Edge.makeThreePointArc(cq.Vector(*p['start']),cq.Vector(*p['mid']),cq.Vector(*p['end']))for p in pr if p['lengthMm']>1e-8];path=cq.Wire.assembleEdges(edges);a=pr[0]['start'];b=pr[0]['end'];s=cq.Workplane(cq.Plane(origin=cq.Vector(*a),normal=cq.Vector(*[y-x for x,y in zip(a,b)]))).circle(row['radiusMm']).sweep(cq.Workplane('XY').newObject([path]),isFrenet=True)
 assert abs(path.Length()-sum(q['lengthMm']for q in pr))<1e-6
else:
 a,b=row['boundsMm'];s=cq.Workplane('XY').box(*[b[i]-a[i]for i in range(3)]).translate(tuple((a[i]+b[i])/2 for i in range(3)))
assert s.val().isValid();key=row['key'];cq.exporters.export(s,str(D/(key+'.step')));cq.exporters.export(s,str(D/(key+'.stl')),tolerance=.02,angularTolerance=.1);bb=s.val().BoundingBox()
r={'key':key,'validNative':True,'volumeMm3':s.val().Volume(),'boundsMm':[[bb.xmin,bb.ymin,bb.zmin],[bb.xmax,bb.ymax,bb.zmax]],'sourceCandidateSha256':hashlib.sha256((D/'candidate.json').read_bytes()).hexdigest(),'file':str(D/(key+'.stl')),'sha256':hashlib.sha256((D/(key+'.stl')).read_bytes()).hexdigest(),'step':str(D/(key+'.step')),'stepSha256':hashlib.sha256((D/(key+'.step')).read_bytes()).hexdigest()};(D/(key+'-export.json')).write_text(json.dumps(r,indent=2)+'\n');print(key,r['volumeMm3'])
