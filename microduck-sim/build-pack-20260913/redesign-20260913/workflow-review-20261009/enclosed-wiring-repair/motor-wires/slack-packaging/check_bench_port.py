from pathlib import Path
import json,hashlib,sys
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;A=M.parent/'ankle-wires';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(s.status())=='Error.NoError' and s.volume()>0;return s
m=json.loads((D/'mixed-leg-manifest.json').read_text());ports=sorted({r[k]for r in m['routes']for k in ['fromPort','toPort']});key=ports[int(sys.argv[1])];p=json.loads((M/'active-topology.json').read_text())['ports'][key];part=next(x for x in m['parts']if x['key']==key);plugmesh=trimesh.load_mesh(part['file']);plug=solid(plugmesh);T=np.array(p['transform']);native=[b for b in json.loads((A/'native-motors/manifest.json').read_text())['parts']if b['motor']==2];out=[];fail=[]
for n in native:
 b=trimesh.load_mesh(n['file']);b.apply_transform(T@np.linalg.inv(n['worldTransform']));s=solid(b);vs=[]
 for i in range(13):
  d=np.array(p['outward'])*i;cut=plug.translate(d.tolist())^s;vs.append(cut.volume())
 # Own mated catalogue box retains known exact interface conflicts; permit no increase during axial motion.
 limit=vs[0]+1e-5;bad=[i for i,v in enumerate(vs)if v>limit];row={'solid':n['solid'],'sourceSha256':sha(n['file']),'seatedVolumeMm3':vs[0],'volumesByWithdrawalMm':vs,'maximumAdditionalVolumeMm3':max(vs)-vs[0],'failedSamplesMm':bad};out.append(row)
 if bad:fail.append(row)
r={'port':key,'scope':'Isolated motor bench only; all leg covers and adjacent motors excluded by explicit pre-seat station','passed':not fail,'outwardAxisWorld':p['outward'],'motionRangeMm':[0,12],'sampleSpacingMm':1,'seatedAtMm':0,'prepareAtMm':12,'sourceHousingFile':part['file'],'sourceHousingSha256':sha(part['file']),'sourceTopologySha256':sha(M/'active-topology.json'),'checks':out,'physicalMatingVerified':False,'matingBoundary':'Manufacturer compatible EHR catalogue maximum receiving box, not exact plug profile. Known own seated overlap caps are per solid; no extra traversal allowed.'};(D/f'bench-port-{sys.argv[1]}.json').write_text(json.dumps(r,indent=2));print(key,r['passed'],[(x['solid'],x['failedSamplesMm'],x['maximumAdditionalVolumeMm3'])for x in fail]);assert r['passed']
