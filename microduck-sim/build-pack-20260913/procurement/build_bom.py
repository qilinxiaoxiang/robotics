"""Generate the English procurement snapshot from the English catalog and actual cart evidence. No store writes or purchases."""
from redesign_procurement import active as _redesign_active, build_bom as _redesign_run
if _redesign_active():
    _redesign_run()
    raise SystemExit(0)

# Legacy implementation and its original proof checks are retained below.
from pathlib import Path
import json,datetime,collections,hashlib
from sourcing import load_policy, apply_policy, validate_selection
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent.parent
items=json.loads((OUT/'catalog-en.json').read_text())
policy=load_policy(items)
robot='https://robotis.us/products/'
# Cart observations may update a matching quote, never engineering quantity or supplier choice.
by_id={x['id']:x for x in items}
for source_name in ['cart-status-root.json','cart-status-procurement.json']:
 source=OUT/source_name
 if not source.exists():continue
 for cart in json.loads(source.read_text()).get('stores',[]):
  if cart.get('status')!='cart_verified':continue
  for line in cart.get('lines',[]):
   item_id=line.get('bom_item_id',line.get('item_id'))
   if item_id not in by_id or policy['items'][item_id]['decision']!='buy':continue
   target=by_id[item_id]['purchase']
   if line.get('product_url')!=target['url'] or line.get('quantity')!=target['packages']:continue
   if {'ROBOTIS':'ROBOTIS US'}.get(cart['store'],cart['store'])!=target['store']:continue
   total=line.get('line_total_usd')
   if total is not None:target.update(unit_price_usd=round(total/target['packages'],6),subtotal_usd=total,stock_status='cart_verified')
items=apply_policy(items,policy)
validate_selection(items,policy)
# Bring in original community print inventory without claiming every included duplicate is installed.
inv=ROOT/'build-pack-20260913/assembly/community-print-inventory.json'
original=json.loads(inv.read_text()) if inv.exists() else None
manifest_path=ROOT/'build-pack-20260913/assembly/print-manifest.json'
manifest=json.loads(manifest_path.read_text())
prints=[dict(id=x['name'],file=str(manifest_path.parent/x['file']),quantity=x['quantity'],sha256=x['sha256'],source='current_print_manifest',status='current_eleven_slice_verified') for x in manifest['instances'] if '/current/' in x['file']]
assert len(prints)==11
result={'schema_version':1,'problem_ids':['P5','P6'],'title_zh':'MicroDuck procurement snapshot: quotes and installation evidence separated','verified_date_local':'2026-09-13','destination_region':'Pittsburgh, PA, USA','destination_zip':None,'currency':'USD','no_order_placed':True,'shipping_and_tax_status':'ROBOTIS shipping 16.74; DigiKey shipping estimate4.99 and tariff6.24. Additional final tax is not confirmed.','design_scope':'Phase1: 15 XL330-M288-T including jaw, OpenRB150, borrowedPiZero2W, torsoBNO085, single existing Xiaomi bank, 12V PD receiver, common 5V regulator, and fused motor/logic branches. Camera,audio and onboard battery deferred toPhase2. See ../phase1/START-HERE.html for exactcurrentprint andacceptance route.','items':items,'modified_print_parts':prints,'original_print_inventory_source':str(inv),'original_print_inventory':original,'excluded_items':['Game controller; computer control retained','Wi-Fi dongle; PiZero2W has Wi-Fi','Separate servo output horns; XL330 integrated output','Old large external backpack','Old HAT/speaker/top-head-shell/power-support replaced by final design','Li-ion NP-F970 pack and old BMS/power scheme','Old bulky automotive fuse holder','STL envelopes/proxies/assembly-only meshes'],'alternatives':[{'id':'domestic_pi_bundle','store':'CanaKit','model':'PI-Z2WH-STR32-C4-BLK','url':'https://www.canakit.com/raspberry-pi-zero-2-w.html?cid=usd','price_usd':89.95,'stock':'Add to Cart exact preheader Starter variant','includes':['PiZero2W preheader','32GB microSD','2.5A MicroUSB PSU','OTG cable','case','heatsink','mini HDMI adapter'],'duplicate_buy_ids_to_remove':['pi','sd','bench_pi_psu'],'notes':'Use Pi board alone in duck; do not add case/heatsink without clearance. Checkout delivery unknown.'},{'id':'camera_us','store':'Adafruit','model':'5658 CameraModule3Wide','url':'https://www.adafruit.com/product/5658','price_usd':38.50,'stock':'in_stock'},{'id':'charger_alternate','store':'HeliDirect','model':'HOTA T6','url':'https://www.helidirect.com/products/hota-t6-dc-charger','price_usd':44.90,'stock':'variant_available','notes':'$0.41 more; expedited shipping needs destination quote.'},{'id':'controller_separate','store':'ROBOTIS US','model':'OpenRB150902-0183-000','url':robot+'openrb-150','price_usd':28.64,'stock':'variant_available','notes':'15 standalone motors+board=$440.99 vs mixed kit=$437.65.'}], 'open_checks':['Original community printed idler/ring vs official metal bearing selection and per-hole fastener count: assembly agent reconciliation pending; do not add both bearing schemes.','Bare MicroB maximum box now passes both Pi ports; USB-C molded connector, strain relief and USB electrical enumeration require physical verification.','Original frame per-hole fasteners and printed bearing implementation need verification; new spacers are integral printed features and do not require purchase.','Unquoted consumables, printer material availability, exact shipment origin and Pittsburgh checkout totals.']}
quoted=[x for x in items if x['category']=='buy' and x['purchase']['subtotal_usd'] is not None]
def sliced_queue(folder,file,**extra):
 source=ROOT/'build-pack-20260913/assembly'/folder/'slice-verification.json'
 data=json.loads(source.read_text())['result']
 assert data['return_code']==0, source
 plates=data['sliced_plates']
 return dict(file=str(source.parent/file),plates=len(plates),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),predicted_g=sum(f['total_used_g'] for pl in plates for f in pl['filaments']),predicted_seconds=sum(pl['total_predication'] for pl in plates),warnings=[pl['warning_message'] for pl in plates if pl['warning_message']],source=str(source),**extra)
result['legacy_print_queues']={'current_eleven':sliced_queue('printing','MicroDuck-current-11-parts-X1C-CoolPlate.3mf',parts=11),'full_queue':sliced_queue('printing-full','MicroDuck-complete-89-instances-X1C-CoolPlate.3mf',instances=89,includes_possible_spares=True),'profile':'Bambu Studio2.7.1.62,X1C0.4,PLA,CoolPlate,0.2mm,4walls,30%infill,tree support','physical_print_completed':False}
result['print_queues']={'phase1':{'manifest':str(OUT.parent/'phase1/print-manifest.json'),'instances':85,'plates':6,'entrypoint':str(OUT.parent/'phase1/PRINT-LIST.md')}}
result['quoted_required_goods_subtotal_usd']=round(sum(x['purchase']['subtotal_usd'] for x in quoted),2)
result['quoted_consumables_subtotal_usd']=round(sum(x['purchase']['subtotal_usd'] for x in items if x['category']=='consumable' and x['purchase']['subtotal_usd'] is not None),2)
result['quoted_print_material_subtotal_usd']=round(sum(x['purchase']['subtotal_usd'] for x in items if x['category']=='print_material' and x['purchase']['subtotal_usd'] is not None),2)
result['all_priced_required_subtotal_usd']=round(result['quoted_required_goods_subtotal_usd']+result['quoted_consumables_subtotal_usd']+result['quoted_print_material_subtotal_usd'],2)
result['unpriced_required_item_ids']=[x['id'] for x in items if x['category'] in ['buy','consumable','print_material'] and x['purchase']['subtotal_usd'] is None]
result['quoted_goods_store_totals_usd']={k:round(sum(x['purchase']['subtotal_usd'] for x in quoted if x['purchase']['store']==k),2) for k in sorted(set(x['purchase']['store'] for x in quoted))}

# Keep legacy *_zh field names for compatibility; all authored values are English.
result['language']='en'
result['selected_route']='One existing bank powers the whole robot via a 12V receiver and common 5V converter. Buy only from ROBOTIS and DigiKey. Raspberry Pi and its accessories are deferred for borrowing. Printing, fasteners and general assembly consumables come from RoboClub first. Purchase only explicit buy items in sourcing-policy.json.'
result['sourcing_policy']=policy
result['alternatives']=[x for x in result['alternatives'] if x['id'] not in ['domestic_pi_bundle','camera_us']]
result['open_checks']=[
 'Exact M2.6x6 TAP idler screws must be obtained from RoboClub; stock is unconfirmed and no separate pack is authorized. Confirm stock before assembly.',
 'Bare Micro-B envelopes passed static checks; USB-C molded shell, solder strain relief and sustained USB enumeration still require physical verification.',
 'Narrow tie thickness/buckles, tape thickness, insulation, flexible routing, final mass and joint clearance require first-article verification.',
 'Bench tools, a fine marker, printer access and checkout shipping/tax/duties remain unconfirmed.',
 'Selected power components support an attended prototype bench workflow only. No real power/thermal/regeneration measurements exist; see ../phase1/power-research.md.'
]
cart_snapshots=[]
for filename in ['cart-status-root.json','cart-status-procurement.json']:
 path=OUT/filename
 if path.exists():
  data=json.loads(path.read_text());cart_snapshots.append(dict(file=filename,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),updated_at=data.get('updated_at'),stores=data.get('stores',[])))
result['actual_cart_snapshots']=cart_snapshots
result['unrelated_preexisting_cart_items']=[{'store':'Pololu','product_id':2815,'quantity':1,'price_usd':8.49,'classification':'Preexisting item outside this BOM; ownership/history not established. Preserved, not counted in project subtotal.'}]
result['quote_boundary']='Quoted goods only, not a complete checkout or total delivered cost. Actual cart evidence remains separate from product-page quotes, stock reservation and physical acceptance.'
(OUT/'bom.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
quotes=[dict(item_id=x['id'],model=x['model'],**x['purchase']) for x in items if x['category'] in ['buy','consumable','print_material'] and x['purchase']['subtotal_usd'] is not None]
(OUT/'quotes.json').write_text(json.dumps({'date':'2026-09-13','language':'en','currency':'USD','source':'bom.json regenerated from catalog-en.json and current actual-cart snapshots','quotes':quotes,'not_checkout':True},indent=2,ensure_ascii=False)+'\n')
lines=['# MicroDuck item checklist','','Verified 2026-09-13 for Pittsburgh, PA, USA. All prices are USD merchandise quotes. Shipping, tax and possible import surcharges are unknown. No order has been placed. Installed quantities are separate from purchased packages.','',f"Quoted required hardware: ${result['quoted_required_goods_subtotal_usd']:.2f}; quoted consumables: ${result['quoted_consumables_subtotal_usd']:.2f}; print material: ${result['quoted_print_material_subtotal_usd']:.2f}; combined quoted items: ${result['all_priced_required_subtotal_usd']:.2f}. This excludes unpriced required items and is not the delivered project total.",'']
labels={'buy':'Required hardware and fasteners','included':'Already included; do not purchase twice','consumable':'Consumables; check existing stock','reuse_or_optional_buy':'Reuse first, otherwise purchase','optional_spare':'Optional spares','reuse_or_borrow':'Reusable or borrowed tools','print_material':'Printing material'}
labels.update(club_supply='RoboClub supply; no purchase',borrow_first='Borrow first; purchase deferred',optional='Optional; no purchase',review_hold='Selection under review; no purchase')
for category,label in labels.items():
 lines+=['## '+label,'']
 for x in [i for i in items if i['category']==category]:
  p=x['purchase']; q=x['installed_quantity']
  qty='Installed consumption or source per-hole count not frozen' if q is None else (f"Bench quantity {x.get('bench_quantity',1)} {x['unit']}; not installed onboard" if q==0 else f"Installed: {q} {x['unit']}")
  package=f"Purchase {p['packages']} package(s), {p['package_content_quantity']} {x['unit']} per package" if p['packages'] else 'No separate purchase'
  price=f"Quoted merchandise subtotal ${p['subtotal_usd']:.2f}" if p['subtotal_usd'] is not None else 'No locked current quote'
  lines+=['### '+x['name_zh'],'',x['model']+'. '+qty+'. '+package+'. '+price+'.','',x['role_zh']+' '+x['notes_zh'],'']
  if p['url']:lines += [f"[Supplier page]({p['url']}) · Status: {p['stock_status'].replace('_',' ')}; checked {p['checked_date']}.",'']
lines+=['## Current print route','','Use only the [85-instance Phase 1 print list](../phase1/PRINT-LIST.md), six plates. The older 89-instance and eleven-part queues are historical references, not additional orders.','']
(OUT/'CHECKLIST.md').write_text('\n'.join(lines))
(OUT/'CHECKLIST.zh.md').write_text('# Checklist moved\n\nThe canonical English checklist is [CHECKLIST.md](CHECKLIST.md). This legacy filename is retained only as a compatibility link.\n')
print(json.dumps({'items':len(items),'modified_print_parts':len(prints),'quoted_goods_usd':result['quoted_required_goods_subtotal_usd'],'quoted_consumables_usd':result['quoted_consumables_subtotal_usd'],'combined_quoted_usd':result['all_priced_required_subtotal_usd']},indent=2))
