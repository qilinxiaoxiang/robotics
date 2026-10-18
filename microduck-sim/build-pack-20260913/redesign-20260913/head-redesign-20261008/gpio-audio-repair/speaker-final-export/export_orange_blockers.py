"""Local support-only modifiers; never normal geometry or global support changes."""
from pathlib import Path
import math,json,hashlib,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;H=D.parents[1];R=H.parent;O=D/'orange-hole-blockers';O.mkdir(exist_ok=True)
report=D/'native-V1-Orange-original-orientation-exclusive/functional-bore-readback.json'
a=json.loads(report.read_text());src=H/'speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'
# H actually gpio-audio-repair parent? Resolve explicit from known file path.
src=D.parent/'speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for f in a['features']:
 if f['name'] not in a['supportCoreIssues']:continue
 origin=np.array(f['origin'],float);axis=np.array(f['axis'],float);axis/=np.linalg.norm(axis)
 lo,hi=f['range'];lo-=.65;hi+=.15
 if f['name']=='speaker-pilot-0':lo=-.4;hi=5.05
 radius=f['radius']+.25;n=64;rr=radius/math.cos(math.pi/n)
 e=np.cross(axis,[0,1,0]);e/=np.linalg.norm(e);v=np.cross(axis,e)
 vertices=[origin+axis*z+rr*(e*math.cos(2*math.pi*i/n)+v*math.sin(2*math.pi*i/n))for z in (lo,hi)for i in range(n)]
 vertices.extend([origin+lo*axis,origin+hi*axis]);faces=[]
 for i in range(n):
  j=(i+1)%n;faces.extend([(i,j,n+j),(i,n+j,n+i),(2*n,j,i),(2*n+1,n+i,n+j)])
 m=tm.Trimesh(vertices,faces,process=True);assert m.is_watertight and m.is_volume
 p=O/(f['name']+'-support-blocker-world.stl');lines=['solid local_support_blocker']
 for tri in m.triangles:
  lines+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(format(float(x),'.17g')for x in q)for q in tri]+['endloop','endfacet']
 lines+=['endsolid local_support_blocker'];p.write_text('\n'.join(lines)+'\n');back=tm.load(p,force='mesh');assert back.is_watertight and back.is_volume
 rows.append({'name':f['name'],'owner':'head_cap','subtype':'support_blocker','frame':'world','worldAxis':axis.tolist(),'worldOrigin':origin.tolist(),'axisRangeMm':[lo,hi],'radiusMm':radius,'worldMesh':str(p),'worldMeshSha256':sha(p),'watertight':True,'positiveVolumeMm3':float(back.volume),'baselineCoreSupportLineCount':f['coreSupportLinesCount']})
r={'integrationReady':True,'modifiesPrintedGeometry':False,'blockers':rows,'sourceCapSha256':sha(src),'sourceCap':str(src),'baselineFunctionalReportSha256':sha(report),'instruction':'Attach as support_blocker subparts to head_cap; apply SAME printTransform as head_cap, then same build-item placement exactly once. Do not load as normal_part. The modifiers only suppress support locally; the source CAD is unchanged. Native reslice and bore audit are required.','independentGeometryIssue':'speaker-pilot-1 has source native roof entering screw engagement corridor; its correction is separate and is not fixed by these five support modifiers.'}
(O/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
