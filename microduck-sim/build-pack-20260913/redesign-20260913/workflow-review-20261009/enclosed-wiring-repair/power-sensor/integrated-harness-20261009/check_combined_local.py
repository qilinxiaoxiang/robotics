from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 m=trimesh.load(p,force='mesh');s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
j=json.loads((D/'junction-space.json').read_text());f=json.loads((D/'distribution-feeds.json').read_text());rows=[]
for a in j['parts']:
 for b in f['parts']:
  x=load(a['file']);y=load(b['file']);c=x^y;v=c.volume();same=a['key']==b['junctionReceivingKey']
  rows.append({'junction':a['key'],'wire':b['key'],'volumeMm3':v,'status':'CLEAR' if c.is_empty() else 'NAMED_SAME_NET_INSULATION_ENVELOPE' if same else 'FAIL','scope':'A receiving envelope deliberately surrounds its own conductor/splice; opposite polarity has no exception'})
assert len(rows)==8
out={'expectedPairs':8,'complete':True,'passed':all(r['status']!='FAIL' for r in rows),'rows':rows,'sourceHashes':{str(p):sha(p) for p in [D/'junction-space.json',D/'distribution-feeds.json',Path(__file__)]+[Path(x['file']) for x in j['parts']+f['parts']]}}
(D/'combined-local-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['rows']))
