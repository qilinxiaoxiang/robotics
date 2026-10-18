import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
OUT=Path(__file__).resolve().parent

def line(item,model,qty,total,url,package=None):
    r=dict(item_id=item,model=model,quantity=qty,line_total_usd=total,product_url=url)
    if package:r['package']=package
    return r

def store(name,tab,url,total,lines,**kw):
    return dict(store=name,tab_id=tab,url=url,status='cart_verified',subtotal_usd=total,lines=lines,mark_handoff=True,**kw)
rows=[
store('Gens ace / Tattu US','1892316957','https://www.genstattu.com/cart.php',25.97,[
line('battery','GEA8502S60E2',1,17.99,'https://www.genstattu.com/gens-ace-850mah-7-4v-60c-2s1p-lipo-battery-pack-with-ec2-plug/'),
line('ec2_leads','GEAX6F2E2M',2,7.98,'https://www.genstattu.com/gens-ace-xt60-female-to-ec2-charging-cable/')]),
store('Buddy RC','1892316963','https://www.buddyrc.com/cart',3.00,[
line('balance_leads','EPB-9432: 8 inch 2S JST-XH balance extension',2,3.00,'https://www.buddyrc.com/products/2s-jst-xh-balance-extension-cable?variant=30735562539094')]),
store('OutOfDarts','1892316966','https://outofdarts.com/cart',7.57,[
line('main_wire','16 AWG silicone wire, red/black pair per foot',2,2.58,'https://outofdarts.com/products/16-awg-silicone-wire-by-the-foot?variant=14314617634858','2 feet red + 2 feet black total'),
line('lipo_bag','LiPo Charging Bag / Transport Bag, Misprinted Logo',1,4.99,'https://outofdarts.com/products/lipo-charging-bag?variant=44666207371306')]),
store('Pyrodrone','1892316975','https://pyrodrone.com/cart',15.97,[
line('branch_wire','X8-1424-20: 20 AWG silicone wire',2,11.98,'https://pyrodrone.com/products/silicone-wire?variant=16927272861739','Each set: 1 m red + 1 m black'),
line('audio_wire','X8-1424-24: 24 AWG silicone wire',1,3.99,'https://pyrodrone.com/products/silicone-wire?variant=16927242911787','1 m red + 1 m black')]),
store('RaceDayQuads','1892316984','https://www.racedayquads.com/cart',44.49,[
line('charger','HOTA T6 PD 15A 1–6S charger; SKU 22423',1,44.49,'https://www.racedayquads.com/products/hota-t6-pd-15a-1-6s-ac-dc-smart-charger?variant=41289248276593')]),
store('Harfington','1892316978','https://www.harfington.com/cart?viewSource=Header',18.18,[
line('pi_mount_screws','Uxcell a16060200ux0367: M2.5×6 self-tapping pan-head',1,9.11,'https://www.harfington.com/products/p-1033403?variant=42182571000057','100 screws'),
line('m2_25','Uxcell a16110800ux1019: M2×25 machine screws, nuts, washers',1,9.07,'https://www.harfington.com/products/p-1098147?variant=42122298130681','25 sets; nuts also cover the 14 required M2 nuts')],removed_superseded_items=[{'model':'Uxcell f25051600ux0399 M2.6×6 self-tapping, 50 pack','quantity_removed':1,'reason':'Replaced by parent-selected ROBOTIS FPX330-H101 matched screws.'}],dispatch_readback='Both retained lines say In stock, dispatch in 24 hours. This is dispatch, not a delivery promise.'),
store('Monster Bolts','1892316987','https://monsterbolts.com/cart',10.32,[]),
store('DigiKey','1892316960','https://www.digikey.com/ordering/shoppingcart',19.47,[
line('main_fuse','Littelfuse 0251010.MXL / F2320-ND, 10 A',3,3.72,'https://www.digikey.com/en/products/detail/littelfuse-inc/0251010-MXL/700757'),
line('branch_fuse','Littelfuse 0251003.MXL / F2315-ND, 3 A',12,11.34,'https://www.digikey.com/en/products/detail/littelfuse-inc/0251003-MXL/700737'),
line('audio_fuse','Littelfuse 0251.500MXL / F2311-ND, 0.5 A',3,4.11,'https://www.digikey.com/en/products/detail/littelfuse-inc/0251-500MXL/700707'),
line('audio_gain_resistor','YAGEO MFR-25FBF52-100K / 100KXBK-ND, 100 kΩ 1% 1/4 W',3,.30,'https://www.digikey.com/en/products/detail/yageo/MFR-25FBF52-100K/13473')],availability_readback='All four lines: Immediate. Cart warning: one additional processing day.',estimate_only={'shipping_service':'FedEx Ground','shipping_usd':8.49,'tariff_usd':2.38,'total_usd':30.34,'destination_entered':False,'tax_included':False},prior_blocker='Automatic security verification resolved without CAPTCHA interaction.')]
monster=next(x for x in rows if x['store']=='Monster Bolts')
for item,model,variant,price,slug in [
('m2_5','M2×5 DIN 7985A A2 pan-head','38436353164',1.04,'mach-phil-pan-a2-m2'),
('m2_8','M2×8 DIN 7985A A2 pan-head','38436354188',1.07,'mach-phil-pan-a2-m2'),
('m2_12','M2×12 DIN 7985A A2 pan-head','38436355020',1.14,'mach-phil-pan-a2-m2'),
('m2_18','M2×18 DIN 7985A A2 pan-head','38436768844',1.46,'mach-phil-pan-a2-m2'),
('m2_20','M2×20 DIN 7985A A2 pan-head','38436355596',1.37,'mach-phil-pan-a2-m2'),
('m3_10','M3×10 ISO 7380 button-head 12.9 alloy','35216415564',1.43,'socket-button-b12-9-m3'),
('m3_20','M3×20 ISO 7380 button-head 12.9 alloy','35216416332',1.57,'socket-button-b12-9-m3'),
('m3_nuts','M3-0.50 DIN 934 A2 hex nuts','40341941715027',.65,'nuts-din934-a2'),
('m3_washers','M3 DIN 125A A2 flat washers','31351045652563',.59,'washers-din125a-a2')]:
    monster['lines'].append(line(item,model,1,price,f'https://monsterbolts.com/products/{slug}?variant={variant}','10 pieces'))
digi=next(x for x in rows if x['store']=='DigiKey')
digi['lines'].extend([
line('wick','Chip Quik SOLDERWICK1.5 / 315-SOLDERWICK1.5-ND, 1.5mm × 1.524m',1,2.59,'https://www.digikey.com/en/products/detail/chip-quik-inc/SOLDERWICK1-5/14636565'),
line('ties_fuse','Panduit PLT2M-C / 298-1028-ND, nominal 203×2.5×1.1mm',10,2.94,'https://www.digikey.com/en/products/detail/panduit-corp/PLT2M-C/280041','10 individual ties; four fuse loops, six spares'),
line('ties_narrow','Panduit PLT.6SM-C / 298-1016-ND, nominal 71×1.8×0.8mm',20,3.94,'https://www.digikey.com/en/products/detail/panduit-corp/PLT-6SM-C/280029','20 individual ties; 15 used for joined alarm/audio loops and EN switch, five spares'),
line('foam','3M (TC) 4492W-0.5-5 / 1067-4492W-0.5-5-ND, 1/2 inch × 5 yards, 0.787mm nominal',1,11.93,'https://www.digikey.com/en/products/detail/3m-tc/4492W-0-5-5/2649500','Closed-cell PE foam tape; adhesive only on tray side, retain battery-facing release liner; receipt thickness including liner ≤1.0mm'),
line('ties_wide','Panduit PLT3S-C / 298-1033-ND, nominal 292×4.8×1.3mm',10,6.33,'https://www.digikey.com/en/products/detail/panduit-corp/PLT3S-C/280046','10 individual battery ties; DigiKey width conversion 4.83mm fits verified 6.2mm slot. Receipt thickness ≤1.6mm.')])
digi['subtotal_usd']=47.20
digi['availability_readback']='All nine lines: Immediate. Cart warning: one additional processing day.'
digi['estimate_only']['total_usd']=58.07

# Use already researched exact source URLs where available; never infer a new product slug.
bom=json.loads((OUT/'bom.json').read_text())
for r in rows:
    for l in r['lines']:
        item=next((i for i in bom['items'] if i['id']==l['item_id']),None)
        if item:
            l['bom_item_id']=item['id']
            if item['id'] in ['battery','balance_leads','main_wire','lipo_bag','branch_wire','audio_wire']: l['product_url']=item['purchase']['url']
obj=dict(updated_at='2026-09-13T03:32:05-04:00',browser='Chrome, shared user session, browser id 1',orders_placed=False,checkout_complete=False,payment_submitted=False,stores=rows,verified_merchandise_subtotal_usd=round(sum(x['subtotal_usd'] for x in rows),2),shipping_tax_duties='No delivery address entered. All figures exclude unconfirmed shipping and tax. DigiKey alone displays a non-address-verified shipping/tariff estimate, recorded separately.',verification_method='Visible final shopping-cart line items, quantities and subtotal read back through shared Chrome UI.',scope='These eight stores only. Root-owned carts are recorded separately in cart-status-root.json. This is a prepared shopping basket, not a submitted order or a fully confirmed checkout.')
for r in rows:assert round(sum(l['line_total_usd'] for l in r['lines']),2)==r['subtotal_usd'],r['store']
(OUT/'cart-status-procurement.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
print(obj['verified_merchandise_subtotal_usd'])
