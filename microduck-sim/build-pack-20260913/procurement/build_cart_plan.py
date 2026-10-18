"""Generate an English cart recipe and merge recorded real-cart readbacks without making purchases."""
from redesign_procurement import active as _redesign_active, build_cart_plan as _redesign_run
if _redesign_active():
    _redesign_run()
    raise SystemExit(0)

# Legacy implementation and its original proof checks are retained below.
from pathlib import Path
import json,datetime,collections
from sourcing import load_policy, apply_policy, validate_selection, cart_conflicts
from urllib.parse import urlparse,parse_qs
OUT=Path(__file__).resolve().parent
bom=json.loads((OUT/'bom.json').read_text())
policy=load_policy(bom['items'])
bom['items']=apply_policy(bom['items'],policy)
selection_notes={
 'servo':'Fourteen standalone XL330-M288-T. Servo 15 is already in the Starter Kit.',
 'controller':'One OpenRB-150 Starter Kit includes the controller and one XL330. Do not add a bare board.',
 'pi':'CanaKit PI-Z2WH-STR32-C4-BLK, pre-soldered 40-pin header, 32GB microSD and bench accessories included.',
 'camera':'Adafruit 5658 Camera Module 3 Wide, visible-light IR-filter version; neither NoIR nor non-Wide.',
 'main_wire':'16AWG red/black pair by foot. Quantity two gives two feet of each color.',
 'branch_wire':'20AWG, one meter red plus one meter black per set; two sets.',
 'audio_wire':'24AWG, one meter red plus one meter black per set; one set.',
 'branch_fuse':'0251003.MXL axial 3A; ten pieces, nine installed and one spare.',
 'main_fuse':'0251010.MXL axial 10A; two pieces, one installed and one spare.',
 'audio_fuse':'0251.500MXL axial 0.5A; three pieces.',
 'low_voltage_alarm':'DL-Volt-Alarm. Actual cart is Global warehouse; freight and arrival date remain unquoted.',
 'm2_25':'M2x25mm, 25 sets including M2 nuts; do not duplicate nuts.',
 'pi_mount_screws':'M2.5x6mm tapping pan screws, 100-pack; not M2 machine screws.',
 'lipo_bag':'Misprinted Logo variant, not the full-price ordinary logo variant.',
 'enable_switch':'Pololu 1408 contains three switches; cart quantity one pack.',
 'ec2_leads':'GEAX6F2E2M, XT60 female to EC2 male, two adapters; verify gender.',
 'battery':'GEA8502S60E2, 850mAh 2S 60C EC2, non-G-Tech; one pack.',
 'idler_screw_sets':'FPX330-H101 4pcs Set, two packs supply sixteen BHS M2.6x6 TAP screws. At most fourteen installed under the stocking allowance; at least two spare if all fourteen are used. Supports are spare.',
 'filament':'PLA Basic Jade White 10100, 1kg WITH SPOOL; one. Do not substitute a refill or bulk-discount price.'
}
holds={
 'ties_narrow':'Selected Panduit PLT.6SM-C x20; fifteen installed across joined audio/alarm rings and EN, five spare. Await exact cart readback.',
 'ties_wide':'Selected Panduit PLT3S-C x10; two installed battery ties. Await exact cart readback.',
 'ties_fuse':'Selected Panduit PLT2M-C x10; four installed fuse rings. Await exact cart readback.',
 'foam':'Selected 3M TC4492W-0.5-5 x1; nominal 0.787mm plus retained liner where specified. Await exact cart readback.',
 'wick':'Selected Chip Quik SOLDERWICK1.5 x1. Await exact cart readback.'
}
rows=[]
for x in bom['items']:
 p=x['purchase'];c=x['category'];status='hold';reason=holds.get(x['id'],'Exact product, stock or quote remains unresolved.')
 if c in ['buy','consumable','print_material'] and p['subtotal_usd'] is not None:
  status='add_now';reason='Selected model and package recorded. Actual cart readback governs final price/availability; not a purchase or physical acceptance.'
 elif c=='included':status='do_not_add_included';reason=x['notes_zh']
 elif c=='optional_spare':status='do_not_add_optional';reason='Optional spare is excluded from the required basket.'
 elif c in ['reuse_or_borrow','reuse_or_optional_buy']:status='reuse_or_borrow_first';reason='Ownership/access unverified. Do not automatically purchase every bench tool.'
 elif c in ['club_supply','borrow_first','optional','review_hold']:status='do_not_add_'+c;reason=x['sourcing'].get('note','Explicit sourcing decision excludes purchase.')
 rows.append(dict(item_id=x['id'],name_zh=x['name_zh'],model=x['model'],action=status,reason_zh=reason,store=p['store'],product_url=p['url'],variant_id=parse_qs(urlparse(p['url'] or '').query).get('variant',[None])[0],selection_zh=selection_notes.get(x['id'],'Choose the exact listed model, size and package; do not accept an unreviewed recommendation.'),cart_quantity_packages=p['packages'],units_per_package=p['package_content_quantity'],installed_quantity=x['installed_quantity'],quoted_unit_price_usd=p['unit_price_usd'],quoted_subtotal_usd=p['subtotal_usd'],fit_or_use_notes_zh=x['notes_zh']))
 if x['sourcing']['decision']!='buy': rows[-1]['selection_zh']=reason
actual=[]
for fn in ['cart-status-root.json','cart-status-procurement.json']:
 f=OUT/fn
 if f.exists():
  snapshot=json.loads(f.read_text())
  actual.extend(dict(s,source_file=fn,source_updated_at=snapshot.get('updated_at')) for s in snapshot['stores'])
alias={'ROBOTIS':'ROBOTIS US','Bambu':'Bambu Lab US'}
store_data=[]
for shop in sorted({r['store'] for r in rows if r['action']=='add_now'}):
 lines=[r for r in rows if r['store']==shop and r['action']=='add_now']
 evidence=[s for s in actual if alias.get(s['store'],s['store'])==shop]
 store_data.append(dict(store=shop,lines=lines,quoted_subtotal_usd=round(sum(r['quoted_subtotal_usd'] for r in lines),2),actual_cart_evidence=evidence,cart_readback_verified=bool(evidence and evidence[-1].get('status')=='cart_verified'),shipping_usd=None,tax_usd=None,duties_usd=None))
result=dict(schema_version=2,language='en',revision='english_current_selections_and_cart_readbacks',created_at=datetime.datetime.now().astimezone().isoformat(),source_bom=str(OUT/'bom.json'),currency='USD',destination_region='Pittsburgh PA USA',destination_zip=None,route=bom['selected_route'],all_item_classifications=rows,stores=store_data,add_now_quoted_subtotal_usd=round(sum(r['quoted_subtotal_usd'] for r in rows if r['action']=='add_now'),2),unresolved_item_ids=[r['item_id'] for r in rows if r['action']=='hold'],actual_cart_readbacks=actual,shipping_optimization={'status':'Same-parts bounded comparison selects two stores; see whole-order-comparison.json. Final tax and global cheapest-market claims remain excluded.','principle':'Consolidate matching items into already-required stores when supported by exact product evidence.'},cart_execution='Root and procurement agents own Chrome carts. This generator only reads recorded evidence. It makes no store requests or purchases.',orders_placed=False,unrelated_preexisting_cart_items=bom['unrelated_preexisting_cart_items'],physical_acceptance_required=['Original printed idler first fit and source fastener lengths','Bare USB solder envelope, C-end shell and sustained enumeration','Narrow tie thickness/buckle and insulation material dimensions','Flexible harness routing, final onboard mass, voltage drop and heat','All fifteen servos, including jaw, with simultaneous Pi/IMU/OpenRB logic load; camera/audio deferred'])
assert len(rows)==len({r['item_id'] for r in rows})
validate_selection(bom['items'],policy,rows)
result['cart_policy_conflicts']=cart_conflicts(actual,policy)
result['checkout_ready']=not result['cart_policy_conflicts'] and not result['unresolved_item_ids']
result['checkout_ready']=False if result['destination_zip'] is None else result['checkout_ready']
result['sourcing_policy_file']=str(OUT/'sourcing-policy.json')
(OUT/'cart-plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
total=round(sum(s['subtotal_usd'] for s in actual),2)
doc=['# MicroDuck shopping carts','',f"Selected project goods: **${result['add_now_quoted_subtotal_usd']:.2f}**. Recorded cart merchandise: **${total:.2f}**, including the separately identified preexisting Pololu $8.49 item. Displayed shipping/tariffs are recorded in the handbook; final tax and confirmed arrival dates remain unverified. No order placed.",'','Raspberry Pi procurement is deferred while seeking borrowed resources. Printing materials, fasteners and general assembly consumables are sourced from RoboClub first. Exact fit/rating checks remain assembly requirements. See [sourcing decisions](sourcing-policy.json).','',f"Cart-policy conflicts: **{len(result['cart_policy_conflicts'])}**. A nonzero count blocks cart handoff. Only the two buying destinations are displayed below. Empty historical carts and the unrelated Pololu item remain in the JSON audit record.",'']
for cart in [x for x in actual if alias.get(x['store'],x['store']) in {r['store'] for r in rows if r['action']=='add_now'}]:
 doc += [f"## [{cart['store']}]({cart['url']}) - ${cart['subtotal_usd']:.2f}",'',f"Observed: {cart.get('observed_at',cart.get('source_updated_at'))}.",'']
 if not cart['lines']:doc+=['Cart empty after removing deferred or club-supplied items.','']
 for line in cart['lines']:
  name=line.get('model',line.get('item',str(line.get('product_id','Item'))))
  doc += [f"- {name}: quantity {line['quantity']}; ${line['line_total_usd']:.2f}."]
 doc+=['']
doc+=['[Full assembly checklist](CHECKLIST.md) | [Power readiness](../phase1/power-research.md)','']
(OUT/'CARTS.md').write_text('\n'.join(doc))
print(json.dumps({'items':len(rows),'stores':len(store_data),'add_now_usd':result['add_now_quoted_subtotal_usd'],'action_counts':dict(collections.Counter(r['action'] for r in rows))}))
