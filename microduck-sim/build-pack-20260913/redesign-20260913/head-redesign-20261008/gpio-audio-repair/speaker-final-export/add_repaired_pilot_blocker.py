from pathlib import Path
import os,json,math,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import trimesh as tm,numpy as np
D=Path(__file__).resolve().parent;O=D/'orange-hole-blockers';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();a=json.loads((O/'manifest.json').read_text());p=O/'speaker-pilot-1-support-blocker-world.stl';n=64;rad=1.3/math.cos(math.pi/n);lo=133.05;hi=136.69
vs=[[-16+rad*math.cos(i*2*math.pi/n),17+rad*math.sin(i*2*math.pi/n),z]for z in (lo,hi)for i in range(n)]+[[-16,17,lo],[-16,17,hi]];fs=[]
for i in range(n):
 j=(i+1)%n;fs.extend([(i,j,n+j),(i,n+j,n+i),(2*n,j,i),(2*n+1,n+i,n+j)])
m=tm.Trimesh(vs,fs,process=True);assert m.is_volume
s=['solid local_support_blocker']
for tri in m.triangles:s+=['facet normal 0 0 0','outer loop']+['vertex '+' '.join(format(float(x),'.17g')for x in q)for q in tri]+['endloop','endfacet']
s+=['endsolid local_support_blocker'];p.write_text('\n'.join(s)+'\n');assert tm.load(p,force='mesh').is_volume
a['blockers'].append({'name':'speaker-pilot-1','owner':'head_cap','subtype':'support_blocker','frame':'world','worldAxis':[0,0,1],'worldOrigin':[-16,17,133.45],'axisRangeMm':[-.4,3.24],'radiusMm':1.3,'worldMesh':str(p),'worldMeshSha256':sha(p),'watertight':True,'positiveVolumeMm3':float(m.volume),'reason':'Newly opened continuation of same speaker pilot; local support exclusion prevents new support inside this blind engagement corridor.'})
cap=D/'speaker-pilot-fix/cap-speaker-pilot-fixed-world.stl';proof=D/'speaker-pilot-fix/pilot-fix-report.json';a['sourceCap']=str(cap);a['sourceCapSha256']=sha(cap);a['sourceSubsetProof']=str(proof);a['sourceSubsetProofSha256']=sha(proof);a['independentGeometryIssue']='speaker-pilot-1 corrected by separately bound sourceSubsetProof; retained outer-skin thickness is recorded there.';(O/'repaired-cap-manifest.json').write_text(json.dumps(a,indent=2)+'\n');print(O/'repaired-cap-manifest.json')
