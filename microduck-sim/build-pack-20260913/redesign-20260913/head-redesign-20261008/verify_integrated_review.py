"""Cross-check integrated world poses; never certify physical commissioning."""
from pathlib import Path
import base64,hashlib,json,sys
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;G=D.parent/'leg-guide-20261006'
read=lambda p:json.loads((D/p).read_text());sha=lambda p:hashlib.sha256((D/p).read_bytes()).hexdigest()
sys.path.insert(0,str(G/'non-head-review'))
from source_compatibility import validated_equivalent_geometry_source,SourceCompatibilityError
lineage_proofs=[]
def matches_bound_geometry_source(path,expected):
 if not path.is_file():return False
 if hashlib.sha256(path.read_bytes()).hexdigest()==expected:return True
 if path.resolve()!=(G/'full-build-data.json').resolve():return False
 try:proof=validated_equivalent_geometry_source(expected)
 except SourceCompatibilityError:return False
 if not lineage_proofs:lineage_proofs.append(proof)
 return True
def man(m):
 m=m.copy();m.process();s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert s.status()==mf.Error.NoError;return s
c=read('viewer-candidate.json');data=json.loads((G/'full-build-data.json').read_text());meshes={}
for p in data['parts']:
 k=p['key']
 if p.get('partKind')=='fastener' or k in c['removedParts']:continue
 if k in c['replacementMeshes']:m=trimesh.load(D/c['replacementMeshes'][k],force='mesh')
 else:m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
 if k in c['transforms']:m.apply_transform(c['transforms'][k])
 meshes[k]=m
for p in c['additionalParts']:
 if 'screw' in p['key'] or p.get('geometryKind')=='fastener':continue
 meshes[p['key']]=trimesh.load(D/p['mesh'],force='mesh')
solids={k:man(v) for k,v in meshes.items()};rows=[];seen=set();receiving_internal=[];retained_contacts=[]
source_parts={p['key']:p for p in data['parts']}
def source_solid(k):
 p=source_parts[k];return man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
retained_pairs={frozenset(['jaw_frame','motor15']),frozenset(['head_bottom','upper_pad']),frozenset(['face_panel','head_bottom']),frozenset(['face_panel','eye_trim']),frozenset(['face_panel','pi'])}
receiving={p['key']:p.get('receivingAssembly') for p in c['additionalParts']}
# Source mechanical mating contacts are not waived or reclassified here.
# This gate tests each relocated electronic part / camera frame against the
# complete represented assembly; source source pairs retain their own audit.
targets=list(set(c['replacementMeshes'])|set(c['transforms']))+[p['key'] for p in c['additionalParts'] if 'screw' not in p['key'] and p.get('geometryKind')!='fastener']
for k in targets:
 if k not in solids:continue
 for q in solids:
  pair=tuple(sorted([k,q]))
  if k==q or pair in seen:continue
  seen.add(pair);lo,hi=meshes[k].bounds;a,b=meshes[q].bounds
  overlap=0. if np.any(lo>b) or np.any(a>hi) else max(0.,float((solids[k]^solids[q]).volume()))
  if receiving.get(k) and receiving.get(k)==receiving.get(q):
   receiving_internal.append({'parts':[k,q],'intersectionMm3':overlap,'owningAssembly':receiving[k],'meaning':'Overlapping subregions of one composite conservative receiving envelope, not separate physical parts; union checked against external obstacles.'});continue
  if overlap>=1e-4 and frozenset(pair) in retained_pairs:
   source_contact=source_solid(k)^source_solid(q);added=max(0.,float(((solids[k]^solids[q])-source_contact).volume()))
   retained_contacts.append({'parts':[k,q],'sourceMm3':source_contact.volume(),'currentMm3':overlap,'newContactOutsideSourceMm3':added,'stage':'Final seated pose only; no motion allowance','physicalFitVerified':False})
   rows.append({'parts':[k,q],'intersectionMm3':overlap,'passed':added<1e-4,'classification':'Explicit unchanged/reduced source mating contact; physical fit unresolved'});continue
  rows.append({'parts':[k,q],'intersectionMm3':overlap,'passed':overlap<1e-4})
# Negative control: reproduce the superseded controller pose which appeared
# clear only when the neck fork was missing from the hand-picked obstacle list.
p=next(p for p in data['parts'] if p['key']=='openrb')
old=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
old.apply_transform([[.9961947,0,-.0871557,10.371198],[0,1,0,0],[.0871557,0,.9961947,-3.777821],[0,0,0,1]])
negative_overlap=max(0.,float((man(old)^solids['head_yaw_link']).volume()))
negative={'restoredBadControllerPoseVsNeckForkMm3':negative_overlap,'detected':negative_overlap>1e-4,'purpose':'Reject the former layout whose obstacle list omitted the neck fork.'}
curved=read('curved-head/curved-layout.json');retainer=read('camera-retainer/camera-retainer-report.json');checks=[]
def check(ok,label):checks.append({'check':label,'passed':bool(ok)})
check(negative['detected'],'Original controller/neck-fork collision is reproduced by negative control')
check(all(r['passed'] for r in rows),'All replacements and added parts introduce no new static interference; explicit source contacts retained separately')
check(curved['squareCapDifference']['addedVsNativeMm3']>20000,'Rejected rectangular conversion is detected against original curved source')
check(all(Path(D/f).is_file() for f in c['replacementMeshes'].values()),'Every replacement has an actual source mesh')
check(not(set(c['replacementMeshes'])&set(c['transforms'])),'World-space replacements receive no second placement transform')
check(all(sha(p)==h for p,h in c['evidence'].items()),'Configuration binds its current evidence')
bindings=[]
for f in c['evidence']:
 doc=read(f)
 for p,h in doc.get('sourceHashes',{}).items():
  actual=Path(p) if Path(p).is_absolute() else D/p
  bindings.append({'report':f,'source':p,'passed':matches_bound_geometry_source(actual,h)})
check(all(r['passed'] for r in bindings),'Accepted evidence and fragments bind the current owning source files')
check(all(sha(p)==h for p,h in c['meshHashes'].items()),'Every candidate mesh matches its bound hash')
check(hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest()==c['sourceDataSha256'],'Source assembly bytes match the integrated obstacle set')
check(retainer['boardBoundary']['headerOccupancyIncluded'],'Camera frame includes soldered-header receiving envelope check')
check(not retainer['physicalFitVerified'] and not retainer['manufacturingCertified'],'No physical fit or manufacturing certification inferred')
check(read('render-normal-verification.json')['passed'],'Crease shading preserves mesh coordinates')
manifest=read('viewer-manifest.json')
check(manifest['configSha256']==sha('viewer-candidate.json') and manifest['htmlSha256']==sha('HEAD-EYE-REVIEW.html') and manifest['sourceDataSha256']==c['sourceDataSha256'],'Rendered HTML manifest binds the current candidate and source assembly')
report={'passed':all(r['passed'] for r in checks),'checks':checks,'evidenceBindings':bindings,'geometryOnlySourceLineage':lineage_proofs,'retainedSourceContacts':retained_contacts,'negativeControl':negative,'compositeReceivingInternalOverlaps':receiving_internal,'componentPairs':rows,'obstacleKeys':sorted(meshes),'sourceObstacleScope':'All non-fastener source parts, minus explicitly replaced/removed candidate parts; retained structural neck interfaces included.','candidateConfigSha256':sha('viewer-candidate.json'),'htmlSha256':sha('HEAD-EYE-REVIEW.html'),'physicalFitVerified':False,'sourceMechanicalContactScope':'Unmodified motor/ring/jaw mating contacts retain their source audit. Assembly route and tool checks are separate reports.','requiredSeparateEvidence':['camera-retainer/camera-retainer-report.json','curved-head closure/retention checks','jaw-access checks','complete cable route and physical receiving dimensions']}
(D/'integrated-review-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'pairs':len(rows),'failures':[r for r in rows if not r['passed']],'failedChecks':[r for r in checks if not r['passed']]}));raise SystemExit(not report['passed'])
