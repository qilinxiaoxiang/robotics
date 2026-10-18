from pathlib import Path
import re,json,hashlib,gzip,base64,gc
O=Path(__file__).resolve().parent;R=O.parents[4];G=R/'leg-guide-20261006';S=R.parents[1];C=S/'cloud-share';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Existing saved bundle, no adapter regeneration and no geometry/CAD work.
h=(G/'LEFT-LEG.html').read_text();at=h.index('const WIRING=')+len('const WIRING=');w,_=json.JSONDecoder().raw_decode(h,at)
sp=re.search(r'const spatialPacked="([A-Za-z0-9+/=]+)"',h);s=json.loads(gzip.decompress(base64.b64decode(sp[1])));del h;gc.collect()
cs={c['id']:c for c in w['connections']};sc={c['id']:c for c in s['connections']}
issue=[]
for key,c in cs.items():
 x=sc.get(key,{});kind='checked-leg'if x.get('checkedLegRoute') else'checked-local'if x.get('checkedHarnessRoute') else'legacy-segments'if x.get('segments')else'no-geometry'
 if kind not in ['checked-leg','checked-local']:issue.append({'id':key,'purpose':c.get('purpose'),'kind':kind,'geometryStatus':c.get('geometryStatus'),'spatialSegments':len(x.get('segments',[]))})
def text_hits(obj,prefix=''):
 out=[]
 if isinstance(obj,str):
  if re.search(r'(?i)fuse|450.?mA|rooftop|roof.{0,15}(hole|USB)',obj):out.append({'path':prefix,'text':obj[:1000]})
 elif isinstance(obj,dict):
  for k,v in obj.items():
   if not any(t in k.lower()for t in ['b64','sha256','sourcehash','base64','packed','vertices','indices']):out+=text_hits(v,prefix+'.'+k)
 elif isinstance(obj,list):
  for i,v in enumerate(obj):out+=text_hits(v,prefix+f'[{i}]')
 return out
out={'sources':{str(G/'LEFT-LEG.html'):sha(G/'LEFT-LEG.html')},'bundleAdapters':[k for k in w if'Adapter'in k],'connectionCount':len(cs),'remainingNonCheckedConnections':issue,'activeInstructionHits':text_hits(w),'spatialAssertionHits':text_hits({k:v for k,v in s.items()if k not in ['currentParts','checkedHarnessMeshes','connections']})}
(O/'effective-readback.json').write_text(json.dumps(out,indent=2)+'\n');print('bundle adapters',out['bundleAdapters']);print('unaccepted',[(p['id'],p['kind'])for p in issue]);print('fuse hits',[(p['path'],p['text'][:140])for p in out['activeInstructionHits']if'fuse'in p['text'].lower()]);print('spatial assertions',out['spatialAssertionHits'][:10])
