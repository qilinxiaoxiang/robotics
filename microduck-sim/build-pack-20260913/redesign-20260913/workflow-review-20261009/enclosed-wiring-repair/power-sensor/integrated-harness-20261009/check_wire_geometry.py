from pathlib import Path
import json,hashlib,ast
from wire_geometry import primitives,sample,self_check,SOURCE
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[];hashes={str(f):sha(f)for f in [D/'wire_geometry.py',Path(__file__),SOURCE]}
for name in ['zone-feeds.json','head-trunk.json','data-boundary.json']:
 f=D/name;j=json.loads(f.read_text());hashes[str(f)]=sha(f)
 for p in j['parts']:
  pr=p['primitives'];pts,t=sample(pr);test=self_check(pr,pts,p['receivingDiameterMm']);rows.append({'key':p['key'],'file':p['file'],'sha256':p['sha256'],'selfCheck':test,'acceptedForCurrentRenderer':name!='data-boundary.json'})
# Reconstruct only the finite source point declarations, never execute CAD/export code.
f=D/'build_distribution_feeds.py';tree=ast.parse(f.read_text());loop=next(n for n in tree.body if isinstance(n,ast.For))
for tup in ast.literal_eval(loop.iter):
 env=dict(zip(['net','y0','y','jy'],tup))
 for node in loop.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Tuple) for t in node.targets):break
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(f),'exec'),{},env)
 pr=primitives(env['ps'],6);q,t=sample(pr);rows.append({'key':'distribution_'+env['net']+'_whole','controlPoints':env['ps'],'selfCheck':self_check(pr,q,3.2),'acceptedForCurrentRenderer':True})
hashes[str(f)]=sha(f)
negative=[[-.5,-9.5,22],[-.5,-9.5,24.5],[-.5,-11.5,24.5],[13,-11.5,24.5]]
try:primitives(negative,2);raise RuntimeError('Negative control accepted')
except AssertionError as e:failure=str(e)
o={'passed':all(r['selfCheck']['passed']for r in rows),'complete':len(rows)==10,'expectedPaths':10,'rows':rows,'negativeControl':{'oldLeftGroundShortTurnPoints':negative,'rejected':True,'reason':failure},'sourceHashes':hashes,'scope':'Every path made by this local line/arc generator, plus both original native DFR source polylines; DATA candidates are self-checked but not static-accepted. Conservative sampled nonlocal clearance and exact corner-trim nonoverlap. Does not claim a physical wire bend rating.'}
(D/'wire-geometry-check.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps({'passed':o['passed'],'complete':o['complete'],'paths':len(rows),'minimumMargins':[r['selfCheck']['minimumConservativeBetweenSamplesMm']-r['selfCheck']['receivingDiameterMm']for r in rows]}))
