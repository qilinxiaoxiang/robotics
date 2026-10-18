from pathlib import Path
import json,trimesh,numpy as np
D=Path(__file__).resolve().parent;W=D.parents[1];m=json.loads((D/'manifest.json').read_text());base=json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text());obs={p['key']:p for p in base['parts']};routes=json.loads((D/'routes.json').read_text())['routes'];out=[]
for key in ['i2s_pin_20']:
 p=next(p for p in m['parts'] if p['key']==key);a=trimesh.load(p['file'],force='mesh');q=obs['jaw_support'];b=trimesh.load(q['file'],force='mesh');r=trimesh.boolean.intersection([a,b],engine='manifold');pts=np.array(next(p for p in routes if p['key']==key)['centerlineMm']);bb=r.bounds
 mask=np.all(pts>=bb[0]-1,axis=1)&np.all(pts<=bb[1]+1,axis=1)
 out.append({'wire':key,'obstacle':'jaw_support','volumeMm3':float(r.volume),'boundsMm':bb.tolist(),'indices':np.flatnonzero(mask).tolist(),'nearPoints':pts[mask].tolist()})
(D/'i2s20-localization.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
