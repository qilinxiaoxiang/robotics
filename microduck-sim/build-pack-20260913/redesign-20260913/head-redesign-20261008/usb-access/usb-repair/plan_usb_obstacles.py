"""Conservative, bounded USB broad phase over the complete sampled joint domain.

Keeps only source bounds and small transform matrices, never transformed meshes.
Every selected obstacle still requires a single-obstacle exact check.
"""
from pathlib import Path
import argparse,hashlib,itertools,json,os,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Use run_bounded_cad.py'
import numpy as np
D=Path(__file__).resolve().parent;H=D.parent.parent
sys.path.insert(0,str(H/'gpio-audio-repair'))
from amp16_aabb_precheck import bounds
FK=H.parent.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py'
sys.path.insert(0,str(FK.parent));from assembly_fk import fk,XML
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--self-results',type=Path,required=True)
p.add_argument('--manifest',type=Path,action='append',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();hashes={}
def read(path):
    path=Path(path);b=path.read_bytes();hashes[str(path.resolve())]=hashlib.sha256(b).hexdigest();return b
def bind(path):
    path=Path(path)
    with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    hashes[str(path.resolve())]=digest;return digest
def data(path):return json.loads(read(path))
def corners(bb):return np.array([list(x)+[1.] for x in itertools.product(*zip(*bb))])
cfg=data(H/'viewer-candidate.json');cache=D/'robot-source-cache';index=data(cache/'index.json')
assert bind(index['sourceFile'])==index['sourceDataSha256']
parts={}
for k,f in index['parts'].items():
    src=data(cache/f);parts[k]={'bounds':src['bounds'],'body':src['body'],'source':str(cache/f)}
removed=set()
for path,c in [(H/'viewer-candidate.json',cfg)]+[(m,data(m)) for m in a.manifest]:
    if 'baseViewerCandidateSha256' in c:assert bind(H/'viewer-candidate.json')==c['baseViewerCandidateSha256'],'Stale base viewer'
    for source,sha in c.get('sourceHashes',{}).items():assert bind(source)==sha,('Stale manifest source',source)
    removed.update(c.get('removedParts',[]))
    meshes=dict(c.get('replacementMeshes',{}));meshes.update({r['key']:r['mesh'] for r in c.get('additionalParts',[])})
    if 'fullFFC' in c.get('diagnosticGeometry',{}):meshes['camera_ribbon_receiving']=c['diagnosticGeometry']['fullFFC']
    for k,f in meshes.items():
        path=H/f;bind(path)
        parts[k]={'bounds':bounds(path),'body':parts.get(k,{}).get('body','jaw_soft'),'source':str(path)}
for k in removed:parts.pop(k,None)
# These source/candidate USB receiving proxies represent the very plugs being
# tested, not separate material. Keep this exclusion explicit and source-bound.
same_plugs=['pi_usb_receiving','openrb_usb_receiving']
for k in same_plugs:parts.pop(k,None)
usb={}
for span in range(25,81,5):
    r=data(a.self_results/f'span-{span}-diagnostic/self.json')
    assert r['allClear'] and r['coverageComplete']
    for source,sha in r['sourceHashes'].items():assert bind(source)==sha,('Stale USB geometry',source)
    assert r['spanMm']==span and len(r['componentBoundsMm'])==6
    usb[span]={k:np.array(v).reshape(2,3) for k,v in r['componentBoundsMm'].items()}
domain=data(D/'rigid-domain.json')['samples'];assert len(domain)==229
read(FK);read(XML);read(Path(__file__));read(H/'gpio-audio-repair/amp16_aabb_precheck.py')
base,_=fk();baseInv={k:np.linalg.inv(v) for k,v in base.items()}
partCorners={k:corners(v['bounds']) for k,v in parts.items()}
selected={};tested=0;potential=0
for i,case in enumerate(domain):
    pose,_=fk({k:np.deg2rad(v) for k,v in case['jointDegrees'].items()})
    invHead=np.linalg.inv(pose['jaw_soft']@baseInv['jaw_soft'])
    for key,part in parts.items():
        body=part['body'];assert body in pose,('Unknown body',key,body)
        transform=invHead@pose[body]@baseInv[body]
        pp=partCorners[key]@transform.T;lo=pp[:,:3].min(axis=0)-.01;hi=pp[:,:3].max(axis=0)+.01
        for span,components in usb.items():
            hits=[name for name,bb in components.items() if np.all(bb[0]<hi) and np.all(lo<bb[1])]
            tested+=len(components);potential+=len(hits)
            if hits:selected.setdefault(f'{span}:{key}',[]).append({'poseIndex':i,'components':hits,'nativeRigidBlocked':bool(case['nativeShellOriginalBottomIntersectionsMm3'])})
expected=12*len(parts)*len(domain)*6;assert tested==expected
out={'status':'BROAD_PHASE_ONLY','expectedPairs':expected,'coveredPairs':tested,'potentialPairs':potential,'separatedPairs':tested-potential,'obstacleCount':len(parts),'sampleCount':len(domain),'spanCount':12,'selected':selected,'obstacles':parts,'explicitSamePlugExclusions':same_plugs,'sourceHashes':hashes,'assemblyAccepted':False,'dimensionBoundary':'Twelve exploratory SC0727 soft spans, not manufacturer tolerances; intermediate continuous spans and physical dimensions are not certified.','rule':'All selected pairs require exact checks; native blocked states are recorded, never waived.'}
a.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'obstacles':len(parts),'coveredPairs':tested,'potentialPairs':potential,'selectedSpanObstacleJobs':len(selected)}))
