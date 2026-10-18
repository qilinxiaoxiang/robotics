"""Stdlib source projection; no CAD scene allocation."""
import json,hashlib
from pathlib import Path
from amp16_aabb_precheck import bounds,compare,sha
D=Path(__file__).resolve().parent;H=D.parent;O=D/'gpio-fanout/x225/actual4397';M=H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';m=json.loads(M.read_text());old=json.loads((D/'speaker-rewire/scene-plan.json').read_text());idx={k:dict(v) for k,v in old['rows'].items() if not k.startswith('usb')}
for k in m['removedParts']+m['sourceScrewIdsReplaced']+m['omittedOriginalScrewIds']:idx.pop(k,None)
for k,p in m['replacementMeshes'].items():idx[k]={'key':k,'path':str(H/p)}
for p in m['additionalParts']:idx[p['key']]={'key':p['key'],'path':str(H/p['mesh'])}
extras={'head_cap':D/'speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl','speaker_wire_0':D/'speaker-rewire/speaker-wire-0-world.stl','speaker_wire_1':D/'speaker-rewire/speaker-wire-1-world.stl','speaker_tie':D/'speaker-rewire/speaker-tie-receiving-world.stl'}
for span in [25,80]:
 for f in (H/f'usb-access/usb-repair/positive-x225-exports/span-{span}-diagnostic').glob('*.stl'):extras[f'usb{span}_{f.stem}']=f
for k,f in extras.items():idx[k]={'key':k,'path':str(f)}
for k,r in idx.items():
 if r.get('path'):r['boundsMm']=bounds(Path(r['path']))
 r['sourceSha256']=sha(Path(r.get('path') or r['dataFile']))
pairs=[]
for pin in [12,20,35,40]:
 f=O/f'i2s-pin{pin}-world.stl';bb=bounds(f)
 for k,r in idx.items():
  delta=[max(0,bb[0][i]-r['boundsMm'][1][i],r['boundsMm'][0][i]-bb[1][i]) for i in range(3)];gap=sum(v*v for v in delta)**.5;pairs.append({'pin':pin,'key':k,'aabbGapMm':gap,'exactNeeded':gap<.5})
report={'integrationReady':False,'manifest':str(M),'manifestSha256':sha(M),'wireHashes':{str(pin):sha(O/f'i2s-pin{pin}-world.stl') for pin in [12,20,35,40]},'rows':idx,'pairs':pairs,'sourceHashes':{str(p):sha(p) for p in [Path(__file__),M,D/'speaker-rewire/scene-plan.json',O.parent/'i2s-route-proposal.json']},'excluded':'Unaccepted changing FFC diagnostics; two USB endcases checked independently, not combined into a simultaneous assembly.'};(O/'complete-scene-plan.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'total':len(pairs),'exactNeeded':sum(p['exactNeeded'] for p in pairs),'keys':sorted(set(p['key'] for p in pairs if p['exactNeeded']))}))
