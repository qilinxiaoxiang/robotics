from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import json,hashlib,zipfile
H=Path(__file__).resolve().parent
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set();self.tables=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id'in a:self.ids.add(a['id'])
  if tag=='table':self.tables+=1
  for k in ['src','href']:
   if k in a:self.links.append(a[k])
errors=[];parsers={}
for f in H.glob('*.html'):
 p=Tags();p.feed(f.read_text());parsers[f.resolve()]=p
for f,p in parsers.items():
 if p.tables:errors.append([str(f),'table forbidden'])
 for link in p.links:
  u=urlsplit(link)
  if u.scheme or u.netloc:continue
  q=(f.parent/unquote(u.path)).resolve() if u.path else f
  if not q.exists():errors.append([str(f),'missing',link]);continue
  if u.fragment and q in parsers and unquote(u.fragment) not in parsers[q].ids:errors.append([str(f),'missing anchor',link])
m=json.loads((H/'print-manifest.json').read_text())
for r in m['instances']:
 p=H/r['file']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:errors.append([str(p),'sha mismatch'])
sliced={}
expected={'printer_model':'Bambu Lab X1 Carbon','printer_variant':'0.4','nozzle_diameter':['0.4'],'curr_bed_type':'Cool Plate','filament_type':['PLA'],'layer_height':'0.2','wall_loops':'4','sparse_infill_density':'30%','sparse_infill_pattern':'gyroid','enable_support':'1','support_type':'tree(auto)'}
for folder,name,count in [('printing','MicroDuck-current-11-parts-X1C-CoolPlate.3mf',11),('printing-full','MicroDuck-complete-89-instances-X1C-CoolPlate.3mf',89)]:
 d=json.loads((H/folder/'slice-verification.json').read_text());p=H/folder/name
 for r in d['parts']:
  if hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()!=r['sha256']:errors.append([folder,'sliced input has changed',r['path']])
 with zipfile.ZipFile(p) as z:settings=json.loads(z.read('Metadata/project_settings.config'))
 for k,v in expected.items():
  if settings.get(k)!=v:errors.append([str(p),'embedded preset mismatch',k,settings.get(k)])
 ps=d['result']['sliced_plates'];objects=sum(len(x['objects']) for x in ps)
 if objects!=count or d['result']['return_code']!=0 or any(x['warning_message'] for x in ps):errors.append([folder,'slice result mismatch'])
 sliced[folder]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'objects':objects,'plates':len(ps),'input_hashes_checked':len(d['parts']),'embedded_settings':expected}
service=json.loads((H/'service-mounts/verification.json').read_text());assert service['passed']
checks={n:json.loads((H/n).read_text())['passed'] for n in ['head-din7985-check.json','usb-bare-plug-check.json','pi-mount-check.json']}
result={'pages':len(parsers),'broken_links':errors,'tables':sum(p.tables for p in parsers.values()),'print_instances':len(m['instances']),'source_hashes_match':not any('sha mismatch' in e for e in errors),'sliced_bundles':sliced,'service_sampled_check':service['passed'],'static_checks':checks,'passed':not errors and all(checks.values()) and len(json.loads((H/'mouth-motion-coaxial-conditional.json').read_text())['strict_collision_free_sampled_degrees'])==61,'exclusions':['No physical print or assembly','61 clear sampled jaw poses do not prove actual fit or actuated jaw control','No original joint per-hole screw count','No dynamic retest using actual new harness/alarms/fuses masses']}
(H/'delivery-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['passed']
