"""Check exact printable membership, sources and explicit held-part exclusion."""
from pathlib import Path
import hashlib,json,zipfile
D=Path(__file__).resolve().parent; R=D.parent
sha=lambda data:hashlib.sha256(data).hexdigest()
def validate(manifest,geometry,archive):
    assert geometry['manifestSha256']==sha(json.dumps(manifest,indent=2).encode()+b'\n')
    rows={p['id']:p for p in geometry['parts']}
    expected=set()
    for part in manifest['parts']:
        row=rows[part['id']]
        assert row['source']==part['source'] and row['sourceSha256']==sha((R/part['source']).read_bytes())
        assert row['watertight'] and row['connectedBodies']==1 and row['volumeMm3']>0
        assert part['quantity']==1 and part['color'] in ['Yellow','White','Orange','Black']
        assert not any(x in part['key'] for x in ['screw','envelope','receiving','motor'])
        if part['status']=='prototype':
            name='individual-parts/'+row['file'];expected.add(name)
            assert archive[name]==(R/part['source']).read_bytes()
        else:assert 'file' not in row
    assert {k for k in archive if k.endswith('.stl')}==expected
    assert len(expected)==geometry['releaseCount'] and not geometry['physicalFitVerified'] and not geometry['slicingAccepted']
    return expected
def main():
    manifest=json.loads((D/'parts.json').read_text());geometry=json.loads((D/'geometry-manifest.json').read_text())
    with zipfile.ZipFile(D/'REPRINT-PARTS.zip') as z:
        assert z.testzip() is None
        archive={n:z.read(n) for n in z.namelist()}
    expected=validate(manifest,geometry,archive)
    bad=dict(archive);held=next(p for p in manifest['parts'] if p['status']=='hold');bad['individual-parts/held.stl']=(R/held['source']).read_bytes()
    try:validate(manifest,geometry,bad)
    except AssertionError:negative=True
    else:raise AssertionError('Held geometry leaked into download')
    evidence={}
    for name,flag in [('head-redesign-20261008/jaw-access/report.json','jawAssemblySequencePassed'),('fastener-review-20261008/fastener-choice-report.json','passed'),('fastener-review-20261008/fastener-context-report.json','passed'),('fastener-review-20261008/knee-washer-repair.json','passed'),('fastener-review-20261008/knee-washer-context.json','passed')]:
        source=R/name;assert json.loads(source.read_text()).get(flag) is True;evidence[name]=sha(source.read_bytes())
    report={'geometryEvidence':evidence,'passed':True,'listedParts':len(manifest['parts']),'prototypeParts':len(expected),'heldParts':sum(p['status']=='hold' for p in manifest['parts']),'heldPartLeakRejected':negative,'manifestSha256':sha((D/'parts.json').read_bytes()),'geometryManifestSha256':sha((D/'geometry-manifest.json').read_bytes()),'htmlSha256':sha((D/'REPRINT-PLAN.html').read_bytes()),'zipSha256':sha((D/'REPRINT-PARTS.zip').read_bytes()),'slicingAccepted':False,'physicalFitVerified':False}
    (D/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
