from pathlib import Path
import json,sys,os,gc
from contracts import sha
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
p=Path(sys.argv[1]);a=json.loads(p.read_text());o=Path(sys.argv[2])
for f,h in a['sourceHashes'].items():assert sha(f)==h
import numpy as np,trimesh as tm,manifold3d as mf
def load(p):
 m=tm.load(p,force='mesh');assert m.is_watertight and m.is_winding_consistent and m.volume>0,(p,'invalidinput')
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
moving=load(a['moving']['path']);fixed=load(a['fixed']['path']).translate(a['fixed']['translationMm']);bb=np.array(fixed.bounding_box()).reshape(2,3);ab=np.array(moving.bounding_box()).reshape(2,3)
r={'candidateOnly':True,'wholeHarnessAccepted':False,'complete':False,'passed':False,'moving':a['moving']['key'],'fixed':a['fixed']['key'],'sourceHashes':a['sourceHashes']|{str(p):sha(p),str(Path(__file__)):sha(__file__)},'rows':[]}
for i in range(161):
 z=40-i*.25;box=ab+[0,0,z];sep=bool(np.any(box[0]>bb[1]) or np.any(bb[0]>box[1]));v=0;ib=None
 if not sep:
  inter=moving.translate([0,0,z])^fixed;assert inter.status()==mf.Error.NoError;v=max(0,float(inter.volume()));ib=list(inter.bounding_box())if v>1e-7 else None;del inter
 r['rows'].append({'index':i,'offsetZMm':z,'aabbSeparated':sep,'intersectionVolumeMm3':v,'intersectionBoundsMm':ib})
 if i%16==0:o.write_text(json.dumps(r,indent=2)+'\n');gc.collect()
r.update(complete=True,passed=all(x['intersectionVolumeMm3']<=1e-7 for x in r['rows']),peak=max(r['rows'],key=lambda x:x['intersectionVolumeMm3']));o.write_text(json.dumps(r,indent=2)+'\n');print(r['moving'],r['fixed'],r['passed'],r['peak']);sys.exit(0 if r['passed']else 2)
