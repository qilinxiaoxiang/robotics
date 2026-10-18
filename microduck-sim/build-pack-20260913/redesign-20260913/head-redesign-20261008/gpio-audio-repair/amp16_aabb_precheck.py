#!/usr/bin/env python3
"""Streaming STL bounds only. No CAD imports, booleans, or acceptance claim."""
import hashlib
import json
import math
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent
C = H / 'camera-ribbon-repair'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()

def bounds(path):
    lo, hi = [math.inf]*3, [-math.inf]*3
    def add(v):
        for i,x in enumerate(v):
            assert math.isfinite(x), path
            lo[i],hi[i] = min(lo[i],x),max(hi[i],x)
    with path.open('rb') as f:
        head=f.read(84)
        n=struct.unpack('<I',head[80:84])[0] if len(head)==84 else -1
        if path.stat().st_size == 84+50*n:
            for _ in range(n):
                row=struct.unpack('<12fH',f.read(50))
                for j in (3,6,9): add(row[j:j+3])
        else:
            f.seek(0)
            for line in f:
                cols=line.split()
                if cols and cols[0]==b'vertex': add(tuple(float(x) for x in cols[1:4]))
    assert all(math.isfinite(x) for x in lo+hi), path
    return [lo,hi]

def compare(a,b):
    overlap=[min(a[1][i],b[1][i])-max(a[0][i],b[0][i]) for i in range(3)]
    return {'signedOverlapExtentMm':overlap,'aabbOverlap':all(x>0 for x in overlap),
            'separatingAxesMm':{axis:-overlap[i] for i,axis in enumerate('XYZ') if overlap[i]<0}}

def main():
    amp=HERE/'amplifier-terminal-receiving-world.stl'
    original=bounds(amp)
    moved=[[v[i]+(16 if i==0 else 0) for i in range(3)] for v in original]
    paths=[C/f for f in ['pi-lowered-pose-world.stl','zero_w_components-lowered-pose-world.stl',
            'gpio_discrete12_receiving-lowered-pose-world.stl','zero_w_gpio_solder_tails-lowered-pose-world.stl',
            'csi_free_straight_receiving-lowered-pose-world.stl','camera-local-world.stl','retainer-local-world.stl',
            'camera-anchors-local-world.stl','camera-af-additional-receiving-world.stl']]
    paths += sorted(C.glob('*-local-screw-world.stl'))
    paths += [H/'curved-head/openrb-curved-layout-world.stl']
    sources={str(amp):sha(amp),str(Path(__file__).resolve()):sha(Path(__file__).resolve())}
    rows=[]
    for p in paths:
        if not p.exists():
            rows.append({'file':str(p),'missing':True});continue
        sources[str(p)]=sha(p); bb=bounds(p)
        rows.append({'file':str(p),'boundsMm':bb,**compare(moved,bb)})
    for p in [C/'lowered-pose-pair-checks.json',C/'local-camera-report.json']:
        sources[str(p)]=sha(p)
    report={'status':'BOUNDS_PRECHECK_ONLY','integrationReady':False,'cadRun':False,
            'deltaWorldMm':[16,0,0],'amplifierOriginalBoundsMm':original,'amplifierMovedBoundsMm':moved,
            'obstacles':rows,'sourceHashes':sources,
            'limitations':['AABB overlap only identifies a required exact check; it is not a mesh collision.',
            'Disjoint AABBs establish separation only for these source meshes at the recorded static pose.',
            'Does not validate new posts, wiring, screws, tool access, insertion, cap closure or joint motion.',
            'Pi lowered and camera local remain independent, unaccepted design branches.']}
    out=HERE/'amp16-aabb-precheck.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(out),'movedBoundsMm':moved,'rows':[{'file':Path(r['file']).name,**{k:v for k,v in r.items() if k in ('aabbOverlap','separatingAxesMm','signedOverlapExtentMm','missing')}} for r in rows]},indent=2))
if __name__=='__main__':main()
