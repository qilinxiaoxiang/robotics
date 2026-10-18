"""Compare two actual like-for-like order arrangements, including shipping and tariff."""
from pathlib import Path
from decimal import Decimal
import json,datetime
P=Path(__file__).resolve().parent
D=lambda x:Decimal(str(x))
e=json.loads((P/'split-cart-live-comparison.json').read_text())
a=e['split_adafruit'];d=e['split_digikey'];r=e['robotis_unchanged'];restored=e['restored_digikey']
split_lines=a['lines']+d['lines']
normalize=lambda rows:sorted((x['item_id'],x['quantity'],D(x['line_total_usd'])) for x in rows)
assert normalize(split_lines)==normalize(restored['lines'])
for row in [d,restored]:
    assert sum(D(x['line_total_usd']) for x in row['lines'])==D(row['merchandise_usd'])
    assert D(row['merchandise_usd'])+D(row['shipping_usd'])+D(row['tariff_usd'])==D(row['displayed_total_usd'])
assert D(r['merchandise_usd'])+D(r['shipping_usd'])==D(r['displayed_total_usd'])
assert sum(D(x['line_total_usd']) for x in a['lines'])==D(a['merchandise_usd'])
assert e['restored_adafruit']['visible_cart_count']==0
three=D(r['displayed_total_usd'])+D(d['displayed_total_usd'])+D(a['merchandise_usd'])+D(a['lowest_offered_shipping_usd'])
two=D(r['displayed_total_usd'])+D(restored['displayed_total_usd'])
assert two<three
# Prevent later changes from reusing this comparison for a different selected basket.
current=sum([json.loads((P/n).read_text())['stores'] for n in ['cart-status-root.json','cart-status-procurement.json']],[])
nowdk=next(s for s in current if s['store']=='DigiKey');nowada=next(s for s in current if s['store']=='Adafruit')
nowrobotis=next(s for s in current if s['store']=='ROBOTIS')
assert sum(D(x['line_total_usd']) for x in nowrobotis['lines'])==D(r['merchandise_usd'])
for live_key, evidence_key in [('subtotal_usd','merchandise_usd'),('shipping_usd','shipping_usd'),('displayed_checkout_total_usd','displayed_total_usd')]:
    assert D(nowrobotis[live_key])==D(r[evidence_key]), f'ROBOTIS {live_key} changed; refresh whole-order comparison'
    assert D(nowdk[live_key])==D(restored[evidence_key]), f'DigiKey {live_key} changed; refresh whole-order comparison'
assert normalize([dict(item_id=x.get('bom_item_id',x.get('item_id')),quantity=x['quantity'],line_total_usd=x['line_total_usd']) for x in nowdk['lines']])==normalize(restored['lines'])
assert not nowada['lines']
assert nowdk['shipping_usd']==restored['shipping_usd'] and nowdk['duties_usd']==restored['tariff_usd']
result={'checked_at':datetime.datetime.now().astimezone().isoformat(),'observed_at':e['observed_at'],'verdict':'POSITIVE: select the two-store basket within the two actual same-parts order arrangements compared.','same_models_quantities_and_merchandise':True,'two_store_before_sales_tax_usd':float(two),'three_store_before_sales_tax_usd':float(three),'saving_from_consolidation_alone_usd':float(three-two),'shipping_assumption_replaced_with_live_quote':True,'evidence_file':'split-cart-live-comparison.json','final_cart_restored_and_verified':True,'orders_placed':False,'remaining_unestablished_claim':'Final paid total including sales tax. This requires final merchant checkout tax confirmation before user payment; all displayed amounts here consistently exclude sales tax.','scope_exclusion':'No global cheapest-market claim. Earlier exact-model DigiKey search returned no XL330-M288-T results, so a complete one-store basket was not established.'}
result['artifact_paths']={
    'cart_evidence':str(P/'split-cart-live-comparison.json'),
    'calculation':str(P/'whole-order-comparison.json'),
    'report':str(P/'ORDER-COMPARISON.md'),
}
(P/'whole-order-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
(P/'ORDER-COMPARISON.md').write_text(f'''# Actual same-parts whole-order comparison

Observed {e['observed_at']}. Both arrangements use the same models, quantities and $507.73 merchandise. Shipping and tariffs are included; sales tax is excluded consistently.

## Two stores — ${two:.2f}

ROBOTIS: $437.65 merchandise + $16.74 shipping = $454.39. DigiKey: $70.08 merchandise + $4.99 shipping + $6.24 tariff = $81.31.

## Three stores — ${three:.2f}

The alternative carts were actually reconstructed. ROBOTIS remains $454.39. The split DigiKey cart visibly quoted $34.78 merchandise + $4.99 shipping + $6.24 tariff = $46.01. The four Adafruit lines visibly total $35.30 and their checkout offers $6.05 USPS Ground Advantage, giving $41.35 before sales tax. Its separately displayed $2.12 sales tax is excluded to retain the same comparison basis.

## Decision and restored state

**Keep two stores. Consolidation alone saves ${three-two:.2f}**, with one fewer order. This comparison holds the power design fixed, so it does not confuse supplier consolidation with changing the old adapter or regulator selection. The earlier favorable free-DigiKey-shipping sensitivity is no longer needed to establish this result: the actual split order's $4.99 quote was read directly.

After comparison, the eight-line DigiKey basket was restored and visibly read back at $81.31; Adafruit visibly returned to zero items. No order/payment occurred. Final sales tax remains a merchant-checkout step before user payment. This is a bounded comparison of these complete baskets, not a global cheapest-market claim.

[Actual cart inputs and restoration evidence](split-cart-live-comparison.json) · [Calculation result](whole-order-comparison.json) · [Current handbook](../phase1/START-HERE.html).
''')
print(json.dumps(result,indent=2))
