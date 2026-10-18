"""Semantic ledger validation against the immutable reviewed connection anchor."""
import collections,copy,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;G=D.parent;R=G.parent
BASE='7c0c10dd22e44ae6d79bd7f24cf448f49c67b3b14e8e2c2d55f393d16ca5d95d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def compare(ledger,base):
    assert set(ledger)=={'problem_ids','connections','screw_totals_by_spec','source_reports','physical_assembly_verified'}
    assert ledger['problem_ids']==['P5','P6'] and ledger['physical_assembly_verified'] is False
    assert len(ledger['connections'])==129
    seen=set();totals=collections.Counter();fields=0;reconstructed=[]
    for row in ledger['connections']:
        assert row['id'] not in seen;seen.add(row['id'])
        matches=[s for s in base['screws'] if s['id']==row['id'] or s.get('groupId')==row['id']]
        assert matches and sum(s.get('quantity',1) for s in matches)==row['quantity']
        anchor={'id':row['id']}
        for key,value in row.items():
            fields+=1
            if key=='id':continue
            if key in ('quantity','nut_quantity','washer_quantity'):
                anchor[key]=sum(s.get(key,0) for s in matches)
            else:
                assert all(key in s and s[key]==matches[0][key] for s in matches),(row['id'],key)
                anchor[key]=matches[0][key]
            assert anchor[key]==value,(row['id'],key)
        reconstructed.append(anchor)
        totals[row['spec']]+=row['quantity']
    assert dict(totals)==ledger['screw_totals_by_spec']
    assert set(ledger['source_reports'])=={'fastener-audit/electronics-fasteners.json','fastener-audit/joint-fasteners.json'}
    for rel,digest in ledger['source_reports'].items():assert sha(R/rel)==digest
    current_hash=hashlib.sha256(canonical(ledger['connections'])).hexdigest()
    anchor_hash=hashlib.sha256(canonical(reconstructed)).hexdigest()
    assert current_hash==anchor_hash
    return fields,current_hash,anchor_hash
def accept(path,old_expected):
    assert Path(path).resolve()==(R/'assembly-fasteners.json').resolve()
    assert sha(G/'full-build-data.json')==BASE
    ledger=json.loads(Path(path).read_text());base=json.loads((G/'full-build-data.json').read_text())
    fields,content,anchor=compare(ledger,base)
    return {'accepted':True,'oldReportByteHash':old_expected,'currentLedgerSha256':sha(Path(path)),'boundGuideSha256':BASE,'connectionsCompared':129,'fieldsCompared':fields,'currentConnectionContentSha256':content,'reviewedAnchorConnectionContentSha256':anchor,'scope':'Every source connection field and grouped hardware quantity equals the immutable reviewed guide. Totals and current upstream report hashes agree. Exact old ledger bytes are unavailable; the reviewed guide connection projection is the explicit anchor, not a claimed old-byte diff. Geometry/specification/quantity mutations reject regardless of file hash.'}
if __name__=='__main__':
    proposal=json.loads((R/'fastener-review-20261008/fastener-patch-proposal.json').read_text())
    old=proposal['sourceHashes'][str(R/'assembly-fasteners.json')]
    result=accept(R/'assembly-fasteners.json',old)
    a=json.loads((R/'assembly-fasteners.json').read_text());b=json.loads((G/'full-build-data.json').read_text())
    for field,value in [('spec','M2 x 4 TAP'),('quantity',99),('hole_centers_mm',[[0,0,0]]),('passed',False)]:
        bad=copy.deepcopy(a);bad['connections'][0][field]=value
        try:compare(bad,b)
        except AssertionError:pass
        else:raise AssertionError('Mutation not rejected '+field)
    result['negativeMutationsRejected']=4
    (D/'current-ledger-projection-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
