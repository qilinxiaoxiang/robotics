from pathlib import Path
import json,hashlib,gc,sys
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];M=D.parents[1]/'motor-wires';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
h=json.loads((D/'zone-housing-check.json').read_text());source=W/'leg-ports/manufacturer-motor-components.json';j=json.loads(source.read_text());S=np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1.]])
rows=[];mate=[];sources={str(p):sha(p)for p in [Path(__file__),D/'zone-housing-check.json',source]}
mixed=M/'slack-packaging/mixed-leg-manifest.json';mix=json.loads(mixed.read_text());sources[str(mixed)]=sha(mixed)
obs=mix['parts']+mix['retentionContexts']
for n in ['distribution-feeds.json','zone-feeds.json','head-trunk.json','data-boundary-v2.json']:
 p=D/n;sources[str(p)]=sha(p);obs+=json.loads(p.read_text())['parts']
for p in [p for p in h['parts'] if p['port']['motor']==int(sys.argv[1])]:
 a=trimesh.load(p['file'],force='mesh');sa=solid(a);num=p['port']['motor'];T=np.array(p['port']['transform'])@S
 for c in j['solids']:
  if c['index']in j['excludesUninstalledRearIdlerSolids']:continue
  b=trimesh.Trimesh(c['vertices'],c['faces'],process=True);b.apply_transform(T);sb=solid(b);vs=[(sa.translate((np.array(p['port']['outward'])*k*.25).tolist())^sb).volume()for k in range(49)]
  mate.append({'housing':p['key'],'solid':c['index'],'seatedReceivingOverlapMm3':vs[0],'maximumOverlapMm3':max(vs),'volumesMm3':vs,'interpretation':'Catalogue female outer receiving box includes intentional socket pin/body volume; not a detailed material insertion certificate','externalTravelClearAfterWithdrawal7_25mm':max(vs[29:])<1e-7})
  del b,sb
  gc.collect()
 del j
 gc.collect()
 for q in obs:
  b=trimesh.load(q['file'],force='mesh');assert b.is_volume;sources[q['file']]=sha(q['file']);v=0.0
  if not (np.any(a.bounds[1]<b.bounds[0]) or np.any(b.bounds[1]<a.bounds[0])):
   c=sa^solid(b);v=c.volume();del c
  del b
  gc.collect()
  ownwire=(num==5 and(q['key'].startswith('zone_left')or q['key']=='data_12_05'))or(num==10 and(q['key'].startswith('zone_right')or q['key']=='data_openrb_10'))
  rows.append({'housing':p['key'],'obstacle':q['key'],'volumeMm3':v,'status':'NAMED_THREE_CONDUCTORS_ENTER_OWN_HOUSING'if ownwire and v>1e-7 else'CLEAR'if v<1e-7 else'BLOCKED'})
report={'complete':True,'rows':rows,'matingRows':mate,'passedExternalStatic':all(r['status']!='BLOCKED'for r in rows),'matingVerified':False,'sourceHashes':sources};(D/('zone-housing-interfaces-'+sys.argv[1]+'.json')).write_text(json.dumps(report,indent=2)+'\n');print('external',report['passedExternalStatic'],[r for r in rows if r['status']=='BLOCKED'])
