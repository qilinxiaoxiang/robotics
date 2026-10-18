from pathlib import Path
import os,json,subprocess,sys,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;cfg=json.loads((H/'viewer-candidate.json').read_text());local=json.loads((D/'local-candidate-manifest.json').read_text());cache=json.loads((D/'head-source-cache/index.json').read_text())
keys=list(dict.fromkeys(list(cache['parts'])+list(cfg['replacementMeshes'])+[p['key'] for p in cfg['additionalParts']]+list(local['replacementMeshes'])+[p['key'] for p in local['additionalParts']]));skip=set(cfg['removedParts'])|set(local['removedParts']);keys=[k for k in keys if k not in skip]
rows=[];dest=D/'developable-all-pairs.json'
for k in keys:
 subprocess.run([sys.executable,str(D/'check_developable_pair.py'),k],check=True)
 row=json.loads((D/('developable-pair-'+k+'.json')).read_text());rows.append(row);dest.write_text(json.dumps({'accepted':False,'completed':False,'rows':rows},indent=2)+'\n')
r={'accepted':False,'completed':True,'pairCount':len(rows),'rows':rows,'sourceHashes':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D/'check_developable_pair.py',D/'developable-ribbon-fit.json',D/'local-candidate-manifest.json']}};dest.write_text(json.dumps(r,indent=2)+'\n');print('DONE',len(rows),'pairs; contacts',[(a['obstacle'],a['volumeMm3']) for a in rows if a['volumeMm3']>1e-5])
