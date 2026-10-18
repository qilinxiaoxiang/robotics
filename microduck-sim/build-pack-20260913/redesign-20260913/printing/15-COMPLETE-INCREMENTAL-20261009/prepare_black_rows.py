from pathlib import Path
import json,hashlib,struct,re,zipfile,xml.etree.ElementTree as E,math
D=Path(__file__).resolve().parent;R=D.parents[1];P=R/'printing/12-REPAIR-V1-20261008';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();inv=json.loads((D/'black-inventory.json').read_text());S=D/'black-source-print';S.mkdir(exist_ok=True);I4=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
def readtris(p):
 b=Path(p).read_bytes()
 if len(b)>84 and len(b)==84+50*struct.unpack('<I',b[80:84])[0]:return [[tuple(v[i:i+3])for i in (3,6,9)]for v in struct.iter_unpack('<12fH',b[84:])]
 vs=[tuple(map(float,m))for m in re.findall(rb'vertex\s+(\S+)\s+(\S+)\s+(\S+)',b)];return [vs[i:i+3]for i in range(0,len(vs),3)]
def contact(ts):
 z=min(v[2]for t in ts for v in t);a=0
 for t in ts:
  if max(v[2]for v in t)-z>.01:continue
  u=[t[1][i]-t[0][i]for i in range(3)];v=[t[2][i]-t[0][i]for i in range(3)];a+=abs(u[0]*v[1]-u[1]*v[0])/2
 return a,z
rows=[];proof=[]
plate=P/'dual-printer/Black_V1.4_base.3mf'
with zipfile.ZipFile(plate)as z:r=E.fromstring(z.read('3D/3dmodel.model'))
n={'m':r.tag.split('}')[0][1:]};objects={o.attrib['id']:o for o in r.findall('m:resources/m:object',n)};items={o.attrib['objectid']:o for o in r.findall('m:build/m:item',n)}
for p in inv['parts']:
 if p['key']=='imu_cover':continue
 oid=p['v14ObjectId'];o=objects[oid];v=[[float(a.attrib[k])for k in ['x','y','z']]for a in o.findall('m:mesh/m:vertices/m:vertex',n)];tri=[[int(a.attrib[k])for k in ['v1','v2','v3']]for a in o.findall('m:mesh/m:triangles/m:triangle',n)];tf=list(map(float,items[oid].attrib['transform'].split()));vs=[[sum(tf[3*j+i]*a[j]for j in range(3))+tf[9+i]for i in range(3)]for a in v];lo=[min(a[i]for a in vs)for i in range(3)];vs=[[a[i]-lo[i]for i in range(3)]for a in vs];ts=[[vs[i]for i in t]for t in tri];f=S/(p['key']+'-print.stl')
 with f.open('w')as w:
  w.write('solid retained_v14_orientation\n')
  for t in ts:
   w.write('facet normal 0 0 0\n outer loop\n')
   for a in t:w.write('  vertex '+' '.join(format(q,'.17g')for q in a)+'\n')
   w.write(' endloop\nendfacet\n')
  w.write('endsolid retained_v14_orientation\n')
 area,z=contact(ts);assert area>1;rows.append({'key':p['key'],'color':'Black','quantity':1,'path':str(f),'sha256':sha(f),'sourceToPrint':I4,'flatContact':{'minimumAreaMm2':max(1,area*.95)},'decision':p['stockAction'],'replacesStockIds':[s['object_id']for s in p['replacesStock']],'changeReason':p['reason'],'supportBlockers':[],'incrementalEvidence':{'path':str(D/'black-inventory.json'),'sha256':sha(D/'black-inventory.json')}});proof.append({'key':p['key'],'source3mf':str(plate),'source3mfSha256':sha(plate),'objectId':oid,'sourceBuildTransform':tf,'removedTranslationMm':lo,'geometryChange':'Rigid original3mf placement followed by translation only; triangle order/coordinates preserved in float64 ASCII.','bedContactAreaMm2':area,'flatToleranceMm':.01,'sourceMeshTriangles':len(tri)})
for p in [next(p for p in inv['parts']if p['key']=='imu_cover'),inv['otherColorRequired'][0]]:
 if p['key']=='imu_cover':T=[[0,1,0,33],[0,0,1,-.800000011920929],[1,0,0,62.599998474121094]]
 else:T=[[1,0,0,61.400001525878906],[0,1,0,21],[0,0,1,-.800000011920929]]
 T.append([0,0,0,1]);ts=[[[sum(T[i][j]*a[j]for j in range(3))+T[i][3]for i in range(3)]for a in t]for t in readtris(p['source'])];area,z=contact(ts);row={'key':p['key'],'color':p['color'],'quantity':1,'path':p['source'],'sha256':p['sourceSha256'],'sourceToPrint':T,'flatContact':{'minimumAreaMm2':area*.95},'decision':'replacement','replacesStockIds':[s['object_id']for s in p['replacesStock']],'changeReason':p['reason'],'supportBlockers':[],'incrementalEvidence':{'path':str(D/'black-inventory.json'),'sha256':sha(D/'black-inventory.json')}};rows.append(row);proof.append({'key':p['key'],'sourceSha256':p['sourceSha256'],'sourceToPrint':T,'bedContactAreaMm2':area,'flatToleranceMm':.01,'bedMinimumZMm':z,'orientationReason':'Cover rear planar face lies on bed; locating stops face upward.'if p['key']=='imu_cover'else'Existing full bottom flange plane lies on bed; keep source geometry without shaving.','supportBoundary':'No pre-existing retained support blockers. Native slice must check original screw/connector openings; no global support disable.'})
(D/'black-package-rows.json').write_text(json.dumps({'parts':rows,'proof':proof},indent=2)+'\n');print([(r['key'],r['color'],r['flatContact'])for r in rows])
