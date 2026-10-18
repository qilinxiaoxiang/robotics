"""Verify the two qualified September29 offers against native Amazon evidence."""
from pathlib import Path
import hashlib,json,re
from fastener_cart import build_fastener_cart,proof
from sourcing import load_policy
P=Path(__file__).resolve().parent
R=P/'fasteners-amazon-20260929'

def verify():
    items=json.loads((P/'catalog-en.json').read_text());policy=load_policy(items)
    plan=build_fastener_cart(P,policy,items)
    assert plan['status']=='partial_cart_verified' and plan['native_cart_verified'] and not plan['all_required_fasteners_covered']
    manifest=json.loads((R/'offers.json').read_text());cart=json.loads(proof(P,manifest['native_cart_evidence']).read_text())
    dom=proof(P,cart['browser_readback']).read_text();screenshot=proof(P,cart['screenshot'])
    assert screenshot.read_bytes()[:2]==b'\xff\xd8', 'Native screenshot is not a JPEG'
    active=dom.split('  - list "Shopping Cart":',1)[1].split('  - heading "Your Items"',1)[0]
    starts=[m.start() for m in re.finditer(r'^    - checkbox "Select .*? for checkout"',active,re.M)]
    assert len(starts)==2, 'Unexpected active cart line count'
    blocks=[active[a:b] for a,b in zip(starts,starts[1:]+[len(active)])]
    parsed={}
    for block in blocks:
        asin=re.search(r'/gp/product/([A-Z0-9]{10})/',block)[1]
        price=float(re.search(r'^    - generic: \$([\d.]+)$',block,re.M)[1])
        qty=int(re.search(r'group "Quantity is (\d+)"',block)[1])
        parsed[asin]={'package_price_usd':price,'package_quantity':qty}
    expected={'B01L7PDGXO':(6,100,8,'pi_mount_screws'),'B01KXTTSCI':(8,50,3,'tap_m25_8')}
    assert set(parsed)==set(expected)=={o['offer_id'] for o in manifest['selected_offers']}
    for offer in manifest['selected_offers']:
        length,nominal,allocated,key=expected[offer['offer_id']]
        assert parsed[offer['offer_id']]=={k:offer[k] for k in ['package_price_usd','package_quantity']}
        text=proof(P,offer['price_evidence']).read_text()
        assert offer['offer_id'] in text.splitlines()[0]
        assert f'Thread Size: M2.5 x {length}mm' in text
        assert 'Head Size: 4 x 1.5mm' in text and 'Self Tapping' in text
        assert f'Package Content: {nominal}(+/-2%)pcs' in text
        assert f"${offer['package_price_usd']:.2f}" in text
        assert offer['coverage'][0]['item_id']==key and offer['coverage'][0]['allocated_units']==allocated
    assert 'Subtotal (2 items): $20.58' in dom and round(sum(x['package_quantity']*x['package_price_usd'] for x in parsed.values()),2)==plan['selected_merchandise_usd']==20.58
    remaining=plan['remaining_uncovered_units'];nuts=sum(v for k,v in remaining.items() if 'nuts' in k);washers=sum(v for k,v in remaining.items() if 'washer' in k);screws=sum(remaining.values())-nuts-washers
    assert (screws,nuts,washers)==(141,17,8)
    files=[R/'authorization.json',R/'offers.json',R/'native-cart.json',proof(P,cart['browser_readback']),screenshot]+[proof(P,o['price_evidence']) for o in manifest['selected_offers']]
    files += [R/'SCREENING.md', R/'amazon-ux6-small-alternative.txt', R/'amazon-m3-rejected.txt', R/'amazon-robotis-search.txt', R/'amazon-rear-washer-rejected.txt'] + sorted(R.glob('m2-*-candidate.txt'))
    report={'status':'partial_cart_verified','qualified_offers_verified':2,'merchandise_subtotal_usd':20.58,'covered_installed_screws':11,'uncovered_screws':screws,'uncovered_nuts':nuts,'uncovered_washers':washers,'physical_stock_verified':False,'all_required_fasteners_covered':False,'checkout_submitted':False,'unrelated_sourcing_holds_preserved':True,'scope':'Two exact compatible inexpensive offers added to the native cart. Does not certify a complete hardware fastener set.','evidence_sha256':{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
    (R/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    print('FASTENER_CART_ACCEPTANCE '+json.dumps(report,separators=(',',':')))
    return report

if __name__=='__main__':verify()
