import os,json,heapq,sys
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
D=Path(__file__).resolve().parent/('packing-photo' if len(sys.argv)>1 and sys.argv[1]=='photo' else ('packing-amp-free' if len(sys.argv)>1 else 'packing'));shape=tuple(json.loads(((D if (D/'fixed.json').exists() else D.parent/'packing-amp-free')/'fixed.json').read_text())['shape'])
def entries(kind):
 ans=[]
 for name in ([f'{kind}-cardinal-screen.json' if len(sys.argv)>1 else f'{kind}-screen.json',f'{kind}-yaw-screen.json',f'{kind}-tilt-screen.json']+([f'{kind}-partition-screen.json'] if len(sys.argv)>1 and sys.argv[1]=='photo' else [])):
  for row in json.loads((D/name).read_text())['results']:
   mask=np.load(D/f'{kind}-orientation-{row["orientationId"]}.npz')['occupancy']
   for ci,c in enumerate(row['candidates']):
    if c['score']>125:continue
    full=np.zeros(shape,np.uint8);x,y,z=c['gridOrigin'];a,b,d=mask.shape;full[x:x+a,y:y+b,z:z+d]=mask
    ans.append((int.from_bytes(np.packbits(full).tobytes(),'little'),dict(c,orientationId=row['orientationId'],candidateId=ci)))
 return sorted(ans,key=lambda a:a[1]['score'])
pi=entries('pi');rb=entries('openrb');best=[];n=0;skipped=0
for p,a in pi:
 for r,b in rb:
  n+=1
  if len(best)==60 and a['score']+b['score']>best[-1][0]:skipped+=1;continue
  over=(p&r).bit_count();score=a['score']+b['score']+over
  best.append((score,over,a,b));best=sorted(best,key=lambda v:v[0])[:60]
r={'screeningOnly':True,'integrationReady':False,'expectedPairs':len(pi)*len(rb),'completedPairs':n,'best':[{'combinedScore':s,'mutualOccupiedVoxels':v,'pi':a,'openrb':b}for s,v,a,b in best]}
(D/'joint-screen.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['best'][:3],indent=2))
