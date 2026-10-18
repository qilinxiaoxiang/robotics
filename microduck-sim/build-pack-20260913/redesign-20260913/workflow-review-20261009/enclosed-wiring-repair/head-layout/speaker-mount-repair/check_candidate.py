"""Bounded changed-cage/static/assembly/driver checks; no global head certification."""
from pathlib import Path
import os,json,hashlib,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;receipt=json.loads((D/'candidate.json').read_text());src=Path(receipt['sourceManifest']);assert hashlib.sha256(src.read_bytes()).hexdigest()==receipt['sourceSha256'];parts=json.loads(src.read_text())['parts'];checks=[];convex=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(q):
 assert sha(q['file'])==q['sha256'];m=trimesh.load(q['file'],force='mesh');m.apply_transform(q.get('worldTransform',np.eye(4)));s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
 if s.status()!=mf.Error.NoError:
  m=m.convex_hull;convex.append(q['key']);s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
 assert s.status()==mf.Error.NoError;return s
shapes={q['key']:load(q)for q in receipt['parts']};speakerrow=next(q for q in parts if q['key']=='REFERENCE current speaker');speaker=load(speakerrow);caprow=next(q for q in parts if q['key']=='current_cap');cap=load(caprow);mountedCap=cap+shapes['speaker_roof_posts']
def test(stage,a,b,key,sample=None,finalSeat=False):
 A=np.array(a.bounding_box()).reshape(2,3);B=np.array(b.bounding_box()).reshape(2,3);sep=np.any(A[1]<B[0])or np.any(B[1]<A[0]);intersection=None if sep else a^b;v=0. if sep else max(0,intersection.volume());plane=finalSeat and v<1e-5
 checks.append(dict(stage=stage,pair=key,sampleMm=sample,volumeMm3=v,finalSeatingPlaneNumericalContact=bool(plane),bounds=list(intersection.bounding_box())if v>1e-7 else None))
# Every independent obstacle is loaded once; exact current USB/board/header inventory included.
obstacles=[q for q in parts if q['group']!='speaker' and q['key']!='current_cap']
for q in obstacles:
 b=load(q)
 for name,a in shapes.items():test('final changed mount vs full independent inventory',a,b,name+'--'+q['key'])
 # Controller, Pi, amp and their connectors move WITH the populated cap.
 # The cap/speaker group is lowered onto the already-present mechanism. Original
 # cap itself is outside this delta check; changed posts/cage/speaker are included.
 for name,a in ({**shapes,'speaker':speaker}.items() if q['group']=='fixed' else []):
  B=np.array(b.bounding_box()).reshape(2,3);A=np.array(a.bounding_box()).reshape(2,3);A[1,2]+=40
  if np.any(A[1]<B[0])or np.any(B[1]<A[0]):continue
  for dz in np.linspace(40,0,161):test('changed populated-cap subset closure',a.translate([0,0,float(dz)]),b,name+'--'+q['key'],float(dz))
 del b;gc.collect()
# Before mounting the cap: open keeper first, real speaker second, bottom cradle last.
for name,a,fixed in [('speaker_keeper',shapes['speaker_keeper'],{'mountedCap':mountedCap}),('speaker',speaker,{'mountedCap':mountedCap,'keeper':shapes['speaker_keeper']}),('speaker_cradle',shapes['speaker_cradle'],{'mountedCap':mountedCap,'keeper':shapes['speaker_keeper'],'speaker':speaker})]:
 for offset in np.linspace(-15,0,61):
  for key,b in fixed.items():test('detached-cap staged insertion',a.translate([0,0,float(offset)]),b,name+'--'+key,float(offset),finalSeat=abs(offset)<1e-9)
# Driver reaches bottom cradle plane; thread engages roof posts from below.
for i,m in enumerate(receipt['mounts']):
 x,y=m['xyMm'];z=131.44;tool=mf.Manifold.cylinder(25,1.5,circular_segments=48).translate([x,y,z-25]);shaft=mf.Manifold.cylinder(8,1.25,circular_segments=48).translate([x,y,z]);head=mf.Manifold.cylinder(1.7,2.5,circular_segments=48).translate([x,y,z-1.7]);screw=shaft+head
 for key,b in [('cap',mountedCap),('speaker',speaker),('keeper',shapes['speaker_keeper']),('cradle',shapes['speaker_cradle'])]:
  test('detached-cap screwdriver',tool,b,str(i)+'--'+key,finalSeat=True)
  if key!='cap':test('seated screw except deliberate pilot engagement',screw,b,str(i)+'--'+key,finalSeat=True)
 for q in obstacles:
  b=load(q);test('final screw vs independent inventory',screw,b,str(i)+'--'+q['key']);del b
fail=[q for q in checks if q['volumeMm3']>1e-7 and not q['finalSeatingPlaneNumericalContact']]
report=dict(passed=not fail,wholeHeadAccepted=False,physicalFitVerified=False,candidate= str(D/'candidate.json'),candidateSha256=sha(D/'candidate.json'),sourceManifest=str(src),sourceSha256=sha(src),scriptSha256=sha(__file__),expectedStaticPairs=len(shapes)*len(obstacles),completedStaticPairs=sum(q['stage']=='final changed mount vs full independent inventory'for q in checks),checks=checks,failures=fail,conservativeObstacleRepairs=sorted(set(convex)),scope='Changed speaker cage, posts and two fasteners; complete current independent inventory. Detached-cap staged assembly and changed-subset closure. Other head components retain their own pending acceptance.')
(D/'assembly-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':not fail,'checks':len(checks),'failures':fail[:12],'failureCount':len(fail)},indent=2))
