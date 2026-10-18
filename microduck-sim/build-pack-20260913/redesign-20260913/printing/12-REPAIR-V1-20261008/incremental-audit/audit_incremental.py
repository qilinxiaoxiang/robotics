"""Read-only stock comparison; stdlib only, no slicer/CAD/pack mutations."""
import collections
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

OUT = Path(__file__).resolve().parent
V = OUT.parent
R = V.parent.parent
SIM = R.parent.parent
P = R / 'printing'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def triangles(p):
    data=p.read_bytes()
    if len(data)>=84 and 84+50*struct.unpack_from('<I',data,80)[0]==len(data):
        for row in struct.iter_unpack('<12fH',data[84:]):
            yield [row[i:i+3] for i in (3,6,9)]
    else:
        tri=[]
        for line in data.decode().splitlines():
            s=line.split()
            if s and s[0]=='vertex':
                tri.append(tuple(map(float,s[1:4])))
                if len(tri)==3: yield tri;tri=[]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def metrics(p):
    ts=list(triangles(p));origin=ts[0][0];vol=[];areas=[];bounds=[[float('inf')]*3,[-float('inf')]*3]
    for a,b,c in ts:
        vol.append(dot(sub(a,origin),cross(sub(b,origin),sub(c,origin)))/6)
        normal=cross(sub(b,a),sub(c,a));areas.append(math.sqrt(dot(normal,normal))/2)
        for v in (a,b,c):
            for i in range(3):bounds[0][i]=min(bounds[0][i],v[i]);bounds[1][i]=max(bounds[1][i],v[i])
    return dict(path=str(p),sha256=sha(p),triangleCount=len(ts),volumeMm3=abs(math.fsum(vol)),surfaceAreaMm2=math.fsum(areas),boundsMm=bounds)

manifest_path=R/'print-manifest.json'
manifest=json.loads(manifest_path.read_text())
copies_path=P/'copy-manifest.json'
copies=[r for r in json.loads(copies_path.read_text())['copy_records'] if 'manifest_instance_index' in r]
assert len(copies)==len(manifest['instances'])==89
stock=[];cache={}
for row in copies:
    p=Path(row['source']); q=P/row['copy']
    assert sha(p)==sha(q)==row['sha256']
    if str(p) not in cache: cache[str(p)]=metrics(p)
    stock.append(dict(**cache[str(p)],plate=row['plate'],objectId=row['object_id'],instanceIndex=row['manifest_instance_index']))

project=P/'02-PROJECTS/Bambu/current-print-queue.3mf'
with zipfile.ZipFile(project) as z:
    root=ET.fromstring(z.read('Metadata/model_settings.config'))
    names={o.get('id'):next(e.get('value') for e in o.findall('metadata') if e.get('key')=='name') for o in root.findall('object')}
assert len(names)==89
assert all(names[r['object_id']]==Path(r['source']).name for r in copies)
assert 'community-24.stl' not in names.values()
assert 'motor-support-coaxial-print.stl' in names.values()

delivery=json.loads((V/'delivery-V1.3/manifest.json').read_text())
rows=[]
for entry in delivery['files']:
    if not entry['path'].endswith('.stl'):continue
    p=V/'delivery-V1.3'/entry['path'];assert sha(p)==entry['sha256'];m=metrics(p)
    near=sorted(stock,key=lambda s:abs(s['volumeMm3']-m['volumeMm3']))[:3]
    # Absolute+relative allowance is deliberately far greater than float STL rounding.
    # Unequal volumes beyond this allowance rule out rigid geometric equivalence;
    # equal volumes alone would NOT prove equivalence.
    tol=max(.01,m['volumeMm3']*1e-5)
    candidates=[s for s in stock if abs(s['volumeMm3']-m['volumeMm3'])<=tol]
    rows.append(dict(**m,key=p.stem.split('_qty')[0],color=p.parent.name,quantity=int(p.stem.split('_qty')[1]),volumeToleranceMm3=tol,possibleVolumeMatches=candidates,nearestStockByVolume=[dict(path=s['path'],volumeMm3=s['volumeMm3'],surfaceAreaMm2=s['surfaceAreaMm2'],volumeDifferenceMm3=abs(s['volumeMm3']-m['volumeMm3'])) for s in near]))
original=SIM/'build-pack-20260913/assembly/print-parts/community-24.stl'
report={'problemIds':['P5','P6'],'method':'Source manifests + all 89 copied source hashes + actual 89-object native editable 3MF metadata; translation/rotation invariant signed closed-mesh volume and surface area. Bounds and file hashes are not used alone to establish geometry change. Equal volume would require further comparison.','baseline':{'printedUserConfirmation':'2026-10-01 all parts including orange, as recorded in PROJECT-CONTEXT.json and printing/README.md','instanceCount':89,'actualProject':str(project),'actualProjectSha256':sha(project),'objectNames':names,'surfaceQualityOct6':'Optional; no subsequent physical print confirmation assumed. Preserves all source geometries/quantities, so does not alter equivalence.'},'sourceHashes':{str(p):sha(p) for p in [Path(__file__),SIM/'PROJECT-CONTEXT.json',P/'README.md',manifest_path,copies_path,project,P/'10-SURFACE-QUALITY-20261006/README.md',V/'delivery-V1.3/manifest.json']},'parts':rows,'originalCommunity24':metrics(original),'stock':stock,'physicalStockBoundary':'Digital delivered 89-instance baseline is supported by user confirmation. Presence of an unused upstream 3MF object does not prove it was printed. A separate explicit user stock correction would supersede this record.','packMutated':False,'newSlicing':False}
(OUT/'geometric-stock-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
for r in rows:print(r['key'],r['quantity'],'volume',round(r['volumeMm3'],5),'matches',[(Path(x['path']).name,round(x['volumeMm3'],5)) for x in r['possibleVolumeMatches']],'nearest',Path(r['nearestStockByVolume'][0]['path']).name,round(r['nearestStockByVolume'][0]['volumeDifferenceMm3'],5))
print('original24',report['originalCommunity24']['volumeMm3'])
