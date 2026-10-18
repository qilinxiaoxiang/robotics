"""Reconcile all current round-cable bounds with source-bound isolated proofs."""
from pathlib import Path
import hashlib,itertools,json,math,os,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from route_geometry import circular_arc,fillet_polyline
D=Path(__file__).resolve().parent;H=D.parent.parent;hashes={}
def bind(path):
    p=Path(path)
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    hashes[str(p.resolve())]=h;return h
def read(path):bind(path);return json.loads(Path(path).read_text())
def current(r):
    for f,h in r['sourceHashes'].items():assert bind(f)==h,('Stale proof',f)
p=read(D/'positive-x225-usb-plan.json');current(p)
scene=read(D/'positive-x225-obstacle-plan.json');current(scene)
domain=read(D/'rigid-domain.json')['samples']
fkpath=H.parent.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py'
sys.path.insert(0,str(fkpath.parent));from assembly_fk import fk,XML
bind(fkpath);bind(XML);base,_=fk();inv={k:np.linalg.inv(t) for k,t in base.items()}
proofs={}
for path in (D/'positive-x225-round-checks').glob('span*/*-round.json'):
    r=read(path);current(r)
    assert r['allClear'] and r['coverageComplete']
    span=int(path.parent.name.split('-')[1])
    for c in r['checks']:
        assert c['result']['passed'] and c['result']['coverageComplete']
        proofs[(span,c['obstacle'],c['poseIndex'],c['moving'])]=str(path)
bounds={}
for row in p['rows']:
    sc,_=circular_arc(p['piPlugTailMm'],p['piPlugOutwardAxis'],p['scFinalDirection'],10)
    tail=np.array(row['usbAFemaleCableExitMm']);straight=np.linspace(sc[-1],tail,int(np.ceil(np.linalg.norm(tail-sc[-1])/.25))+1)
    sc=np.vstack([sc,straight[1:]])
    ac,_=fillet_polyline(row['acWaypointsMm'],10)
    end=p['cEndArc'];arc,_=circular_arc(end['startMm'],end['incoming'],end['outgoing'],10)
    ac=np.vstack([ac,arc[-2::-1]])
    for name,points in [('scFlexibleReceiving',sc),('acFlexibleReceiving',ac)]:
        chord=np.linalg.norm(np.diff(points,axis=0),axis=1).max();assert chord<=.250001
        radius=2.25+10-math.sqrt(100-(chord/2)**2)+1e-9
        bounds[(row['scFlexibleMm'],name)]=(points.min(axis=0)-radius,points.max(axis=0)+radius)
corners={k:np.array([list(c)+[1] for c in itertools.product(*zip(*r['bounds']))]) for k,r in scene['obstacles'].items()}
separated=proved=0;missing=[];clear_count=0
for i,case in enumerate(domain):
    if case['nativeShellOriginalBottomIntersectionsMm3']:continue
    clear_count+=1;pose,_=fk({k:np.deg2rad(v) for k,v in case['jointDegrees'].items()})
    head_inverse=np.linalg.inv(pose['jaw_soft']@inv['jaw_soft'])
    for key,part in scene['obstacles'].items():
        T=head_inverse@pose[part['body']]@inv[part['body']]
        pts=corners[key]@T.T;lo=pts[:,:3].min(axis=0)-.001;hi=pts[:,:3].max(axis=0)+.001
        for (span,cable),(a,b) in bounds.items():
            if np.any(a>=hi) or np.any(lo>=b):separated+=1;continue
            index=-1 if part['body']=='jaw_soft' else i
            if (span,key,index,cable) in proofs:proved+=1
            else:missing.append({'spanMm':span,'obstacle':key,'poseIndex':i,'proofPoseIndex':index,'moving':cable})
expected=clear_count*len(scene['obstacles'])*len(bounds)
assert separated+proved+len(missing)==expected
bind(__file__);bind(D/'route_geometry.py')
report={'nativeClearSampleCount':clear_count,'obstacleCount':len(scene['obstacles']),
        'expectedPairs':expected,'separatedByExpandedRoundBounds':separated,
        'coveredByContinuousRoundCableProof':proved,'missing':missing,
        'complete':not missing,'sourceHashes':hashes,'assemblyAccepted':False,
        'boundary':'All nominal round USB routes at186 native-clear joint samples; physical dimensions and continuous joint interpolation remain unverified. Source-rigid-blocked poses stay blocked.'}
(D/'positive-x225-round-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('sourceHashes','missing')}))
print(json.dumps({'missing':len(missing),'first':missing[:5]}))
