from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError;return a
rows=[];hashes={str(Path(__file__)):sha(__file__)}
for side in ['right','left']:
 report=D/f'hip-{side}-shared-spline.json';r=json.loads(report.read_text());assert r['passedStatic'];p=r['rows'][0];assert sha(p['file'])==p['sha256'];hashes[str(report)]=sha(report);hashes[p['file']]=p['sha256'];m=trimesh.load_mesh(p['file'],process=True);parts=m.split();assert len(parts)==3
 for i,a in enumerate(parts):
  for j,b in enumerate(parts[:i]):rows.append({'side':side,'strandA':i,'strandB':j,'overlapMm3':(solid(a)^solid(b)).volume()})
passed=all(r['overlapMm3']<1e-7 for r in rows);out={'passed':passed,'scope':'Six between-strand pairs in the exported three-wire illustrations; no articulated motion claim.','rows':rows,'sourceHashes':hashes};(D/'shared-strands-check.json').write_text(json.dumps(out,indent=2));print(out);assert passed
