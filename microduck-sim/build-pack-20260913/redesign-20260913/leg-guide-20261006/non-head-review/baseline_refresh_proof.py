"""Exact canonical rebuild proof for refreshed audit provenance; no geometry waiver."""
from pathlib import Path
import copy,hashlib,json
D=Path(__file__).resolve().parent;G=D.parent;SIM=G.parents[2]
KEY='build-pack-20260913/redesign-20260913/assembly-fasteners.json'
BEFORE='1993ce1fb28549e95001ab29c93c258dd8c65f61cf6dee86f225ae9bf3a767da'
AFTER='810e9696e90679f463473579edf95eb7c602ab001d1d5bad42148a93f8a6a3f3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def validate_documents(base,rebuilt):
    assert base['sourceHashes'][KEY]==BEFORE
    assert rebuilt['sourceHashes'][KEY]==AFTER
    expected=copy.deepcopy(base);expected['sourceHashes'][KEY]=AFTER
    assert canonical(expected)==canonical(rebuilt),'Change beyond the one refreshed provenance digest'
def verify(expected):
    assert expected==BEFORE
    assert sha(G/'full-build-data.json')=='7c0c10dd22e44ae6d79bd7f24cf448f49c67b3b14e8e2c2d55f393d16ca5d95d'
    assert sha(D/'rebuilt-source-after-baseline-check.json')=='91b15fc5e7afa89ae4e48fad6c7f5799080a65af6238065c1d4597878eb29d82'
    assert sha(G/'build_full_guide_data.py')=='53575ee8f759a0b6471f0033c6f0f99cba80a3dc75f45110cafd1766c5ef4c3f'
    base=json.loads((G/'full-build-data.json').read_text());rebuilt=json.loads((D/'rebuilt-source-after-baseline-check.json').read_text())
    validate_documents(base,rebuilt)
    for relative,digest in rebuilt['sourceHashes'].items():
        assert sha(SIM/relative)==digest,relative
    return {'accepted':True,'scope':'Canonical generator reproduced every part, screw, operation and other field; only audit provenance digest changed. New fastener geometry requires its separate revision checks.','before':BEFORE,'after':AFTER,'baseSha256':sha(G/'full-build-data.json'),'rebuiltSha256':sha(D/'rebuilt-source-after-baseline-check.json'),'generatorSha256':sha(G/'build_full_guide_data.py')}
def main():
    result=verify(BEFORE)
    base=json.loads((G/'full-build-data.json').read_text());rebuilt=json.loads((D/'rebuilt-source-after-baseline-check.json').read_text())
    for field in ['parts','screws','modules','coverage','notes']:
        bad=copy.deepcopy(rebuilt)
        if isinstance(bad[field],list):bad[field].append({'unknownChange':True})
        else:bad[field]['unknownChange']=True
        try:validate_documents(base,bad)
        except AssertionError:pass
        else:raise AssertionError('Undetected mutation: '+field)
    result['unrelatedMutationNegativesRejected']=5
    (D/'baseline-refresh-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
