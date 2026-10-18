"""Check the delivered handbook against its current procurement, print and runtime sources."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib, json, re, datetime, zipfile
P=Path(__file__).resolve().parent
class Page(HTMLParser):
    def __init__(self): super().__init__(); self.links=[];self.ids=set();self.images=[];self.tables=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='img':self.images.append(a.get('src',''))
        if tag=='table':self.tables+=1
h=(P/'START-HERE.html').read_text();md=(P/'START-HERE.md').read_text();page=Page();page.feed(h)
errors=[]
for link in page.links+page.images:
    u=urlsplit(link)
    if u.scheme or u.netloc:continue
    if not u.path:
        if u.fragment and u.fragment not in page.ids:errors.append('Missing anchor: '+link)
    elif not (P/unquote(u.path)).exists():errors.append('Missing local path: '+link)
if re.search('[\u3400-\u9fff]',md):errors.append('Non-English text in handbook')
if page.tables:errors.append('Unexpected table')
bom=json.loads((P.parent/'procurement/bom.json').read_text())
buy=[x for x in bom['items'] if x['sourcing']['decision']=='buy']
cart_total=round(sum(x['purchase']['subtotal_usd'] for x in buy),2)
if f'${cart_total:.2f}' not in md or len({x['purchase']['store'] for x in buy})!=2:errors.append('Purchasing handoff mismatch')
contract=json.loads((P/'system-contract.json').read_text())
if contract['revision'] not in md:errors.append('Handbook revision differs from system contract')
for x in buy:
    if x['purchase']['url'] not in md:errors.append('Purchased item missing from handbook: '+x['id'])
for obsolete in ['Mean Well','Tensility','three carts','$514.92','eight installed and two spare','phase1-panorama.png','Do not add a USB PD','both supplies','factory-prewired supply jack','fuses and main fuse secured']:
    if obsolete in md:errors.append('Superseded instruction remains: '+obsolete)
if re.search(r'5\s*V\s*/\s*6\s*A|barrel (?:plug|connector)',md,re.I):errors.append('Old adapter instruction remains')
power=json.loads((P/'power-screen.json').read_text())
if power['revision']!=contract['revision'] or not all(power[k] for k in ['within_whole_source_screen','logic_voltage_screen','motor_voltage_screen']):errors.append('Power screen failure')
carts=sum([json.loads((P.parent/'procurement'/n).read_text())['stores'] for n in ['cart-status-root.json','cart-status-procurement.json']],[])
fees=sum((c.get('shipping_usd') or 0)+(c.get('duties_usd') or 0) for c in carts if c['store'] in ['ROBOTIS','DigiKey'])
if f'${cart_total+fees:.2f}' not in md:errors.append('Displayed shipping/tariff total mismatch')
proc=json.loads((P.parent/'procurement/english-verification.json').read_text())
if proc['sourcing_policy_conflicts'] or not proc['catalog_quote_cart_total_match']:errors.append('Purchasing guard failure')
prints=json.loads((P/'print-manifest.json').read_text())['instances']
count=sum(x['quantity'] for x in prints)
for x in prints:
    if hashlib.sha256(Path(x['file']).read_bytes()).hexdigest()!=x['sha256']:errors.append('Print source changed: '+x['name'])
if count!=85:errors.append('Phase 1 print count mismatch')
assembly=json.loads((P/'assembly-delivery-check.json').read_text())
if assembly['sliced_objects']!=count or assembly['sliced_plates']!=6:errors.append('Slice mismatch')
sim=json.loads((P/'simulation/candidate-regression.json').read_text())
if sim['gait_and_stop_passed']!=sim['count'] or sim['count']!=33:errors.append('Gait regression failure')
off=json.loads((P/'runtime/offline-results.json').read_text())
if off['failures'] or off['errors'] or f"{off['offline_tests']}/{off['offline_tests']}" not in md:errors.append('Runtime test result mismatch')
archive=json.loads((P/'runtime/archive-check.json').read_text());zp=P/'runtime'/archive['archive']
if hashlib.sha256(zp.read_bytes()).hexdigest()!=archive['sha256']:errors.append('Runtime archive hash mismatch')
with zipfile.ZipFile(zp) as z:
    if z.testzip():errors.append('Corrupt runtime archive')
    lock=json.loads(z.read('microduck-phase1/bundle-lock.json'))
    if lock['files']['core.py']!=off['source_hash']:errors.append('Offline tests and delivered runtime differ')
    if lock['files']!=off.get('source_files_sha256'):errors.append('Full tested source manifest differs from delivered runtime')
    for relative,expected in lock['files'].items():
        if hashlib.sha256(z.read('microduck-phase1/'+relative)).hexdigest()!=expected:errors.append('Archive source integrity: '+relative)
        source=P/'runtime'/relative
        if source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()!=expected:errors.append('Edited runtime source not repacked: '+relative)
for required in ['ID15','physical pin1','physical pin6','physical pin3','physical pin5','Torque OFF','Goal Position','five consecutive','soldering','4.0–5.5V','4.75–5.25V']:
    if required.lower() not in md.lower():errors.append('Missing essential instruction: '+required)
r={'checked_at':datetime.datetime.now().astimezone().isoformat(),'passed':not errors,'errors':errors,'handbook_sha256':hashlib.sha256(h.encode()).hexdigest(),'local_links_checked':len(page.links),'embedded_images':len(page.images),'english_only':not bool(re.search('[\u3400-\u9fff]',md)),'tables':page.tables,'purchasing_lines':len(buy),'merchandise_usd':cart_total,'held_cart_conflicts':proc['sourcing_policy_conflicts'],'phase1_print_instances':count,'sliced_plates':6,'simulated_gait_cases':sim['count'],'offline_software_cases':off['offline_tests'],'runtime_archive_sha256':archive['sha256'],'physical_tests':0,'remaining_physical_gates':['Borrow exact Pi and verify club fastener/tool stock','Print, inspect fit and retain actual fastener stack','Inspect harness and instrument loaded and transient supply','Calibrate sensor axes and joints on actual robot','Supported standing, walking and pickup','Five full walk-up, stop, lift-hold-release trials']}
(P/'verification.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
if errors:raise SystemExit(1)
assembly['assembly_guide_sha256']=hashlib.sha256((P/'assembly-audit.md').read_bytes()).hexdigest()
assembly['guide_rechecked_at']=r['checked_at']
(P/'assembly-delivery-check.json').write_text(json.dumps(assembly,indent=2)+'\n')
