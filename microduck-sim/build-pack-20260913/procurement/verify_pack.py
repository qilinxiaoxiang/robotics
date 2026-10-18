"""Verify purchasing consistency, English authored material and current print evidence; no stores/hardware."""
from redesign_procurement import active as _redesign_active, verify as _redesign_run
if _redesign_active():
    _redesign_run()
    raise SystemExit(0)

# Legacy implementation and its original proof checks are retained below.
from pathlib import Path
import json,hashlib,datetime,re
from sourcing import load_policy, validate_selection, cart_conflicts, validate_cart_freshness
P=Path(__file__).resolve().parent
from check_system import check, cart_errors
assert not check(), check()
b=json.loads((P/'bom.json').read_text());c=json.loads((P/'cart-plan.json').read_text());q=json.loads((P/'quotes.json').read_text());by={x['id']:x for x in b['items']}
assert set(by)=={row['id'] for row in json.loads((P/'catalog-en.json').read_text())}
assert {'motor_bench_psu','motor_supply_socket'} <= set(by)
assert by['servo']['installed_quantity']==15 and by['servo']['purchase']['packages']==14
policy=load_policy(b['items'])
assert not cart_errors(b['items'],policy,c['actual_cart_readbacks']),cart_errors(b['items'],policy,c['actual_cart_readbacks'])
validate_cart_freshness(b['actual_cart_snapshots'],c['actual_cart_readbacks'])
validate_selection(b['items'],policy,c['all_item_classifications'])
assert by['pi']['sourcing']['decision']=='borrow_first'
assert by['camera']['purchase']['url']=='https://www.adafruit.com/product/5658'
assert all(by[i]['purchase']['packages']==0 for i in ['sd','bench_pi_psu','usb_otg'])
assert by['usb_otg']['installed_quantity']==0 and by['usb_otg']['bench_quantity']==1
assert by['idler_screw_sets']['purchase']['packages']==0 and by['idler_screw_sets']['installed_quantity'] is None
assert by['filament']['purchase']['packages']==0
for id,model in [('ties_narrow','PLT.6SM-C'),('ties_fuse','PLT2M-C'),('ties_wide','PLT3S-C')]:
 assert model in by[id]['model'] and by[id]['purchase']['packages']==0
assert round(sum(x['subtotal_usd'] for x in q['quotes']),2)==b['all_priced_required_subtotal_usd']==c['add_now_quoted_subtotal_usd']
assert not c['unresolved_item_ids']
assert len(c['actual_cart_readbacks'])==14 and all(x['status']=='cart_verified' for x in c['actual_cart_readbacks'])
conflicts = cart_conflicts(c['actual_cart_readbacks'], policy)
if conflicts:
 # A prior successful report must not survive a changed sourcing decision.
 result = {'checked_at': datetime.datetime.now().astimezone().isoformat(),
           'status': 'BLOCKED_CART_RECONCILIATION',
           'purchasing_handoff_ready': False,
           'sourcing_policy_conflicts': conflicts,
           'reason': 'Historical cart observations contain deferred items. Reconcile and read back actual carts before purchasing handoff.',
           'orders_placed': False}
 (P/'english-verification.json').write_text(json.dumps(result, indent=2)+'\n')
 print(json.dumps(result, indent=2))
 raise SystemExit(2)
for store in c['actual_cart_readbacks']:
 for line in store['lines']:
  if 'bom_item_id' not in line:continue
  selected=by[line['bom_item_id']]
  assert selected['purchase']['url']==line['product_url'],(store['store'],line['bom_item_id'],'cart/BOM product identity mismatch')
  assert selected['purchase']['packages']==line['quantity'],(store['store'],line['bom_item_id'],'cart/BOM quantity mismatch')
for store in c['actual_cart_readbacks']:
 for a,z in [('shipping_estimate_usd','shipping_usd'),('tariff_estimate_usd','duties_usd'),('total_estimate_usd','displayed_checkout_total_usd')]:
  if a in store and z in store:assert store[a]==store[z],(store['store'],'conflicting fee fields',a,z)
actual_cart_total=round(sum(x['subtotal_usd'] for x in c['actual_cart_readbacks']),2)
assert round(actual_cart_total-8.49,2)==b['all_priced_required_subtotal_usd']
assert len(b['modified_print_parts'])==11 and b['print_queues']['phase1']['instances']==85
for i in b['modified_print_parts']:
 f=Path(i['file']);assert f.exists() and hashlib.sha256(f.read_bytes()).hexdigest()==i['sha256'],f
for queue in b['legacy_print_queues'].values():
 if not isinstance(queue,dict):continue
 source=Path(queue['source']); data=json.loads(source.read_text())
 assert hashlib.sha256(source.read_bytes()).hexdigest()==queue['source_sha256']
 assert data['result']['return_code']==0
 for part in data['parts']:
  f=Path(part['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==part['sha256'],f
files=[f for f in P.iterdir() if f.suffix in ['.md','.py','.json'] and f.name not in ['sources-index.json','verification.json','english-verification.json']]
issues=[]
for f in files:
 for n,line in enumerate(f.read_text().splitlines(),1):
  if re.search('[\u3400-\u9fff]',line):issues.append({'file':f.name,'line':n,'classification':'preserved_original_source_path' if 'microduck3D' in line else 'unexpected'})
assert all(x['classification']=='preserved_original_source_path' for x in issues),issues
for f in [P/'README.md',P/'CHECKLIST.md',P/'README.zh.md',P/'CHECKLIST.zh.md']:
 s=f.read_text();assert not re.search(r'^\s*\|.*\|',s,re.M)
 for link in re.findall(r'\]\(([^)]+)\)',s):
  if link.startswith(('http:','https:','#')):continue
  target=Path(link.split('#')[0]);target=target if target.is_absolute() else f.parent/target
  assert target.exists(),(f,link)
r={'checked_at':datetime.datetime.now().astimezone().isoformat(),'language':'en','catalog_items':len(by),'selected_purchase_lines':len(q['quotes']),'combined_quoted_usd':b['all_priced_required_subtotal_usd'],'catalog_quote_cart_total_match':True,'sourcing_policy_conflicts':0,'verified_store_carts':14,'actual_cart_merchandise_total_usd':actual_cart_total,'preexisting_pololu_extra_excluded_usd':8.49,'current_print_hashes_verified':11,'active_phase1_slice_instances':85,'legacy_reference_instances':89,'slice_source_and_part_hashes_verified':True,'unexpected_cjk_matches':0,'preserved_source_path_matches':issues,'raw_supplier_sources_excluded_from_language_scan':True,'local_document_links_verified':True,'markdown_tables':0,'unresolved_sku_ids':c['unresolved_item_ids'],'borrowed_tools_and_marker_ownership_verified':False,'hardware_tests':0,'orders_placed':False,'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
(P/'english-verification.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='files'},indent=2))
