"""Exact anchor-port continuation, two short cuts per group, no loop extension."""
import argparse,json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,manifold3d as mf
import flat_ribbon_geometry as g
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';a=argparse.ArgumentParser();a.add_argument('--part',required=True);o=a.parse_args();rp=O/f'{o.part}.json';sp=O/f'{o.part}.npz';r=json.loads(rp.read_text());assert r['coverageComplete'];assert c.sha(sp)==r['stateSha256'];assert not r.get('portsExtended');z=np.load(sp);b=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));before=b.volume();rows=[]
for i in r['expectedUniqueHeadRelativePoses']:
 previous=b.volume()
 for s in g.channels(i):
  ps=np.array(s['points'])
  for end in [0,-1]:
   t=ps[1]-ps[0] if end==0 else ps[-1]-ps[-2];t=t/np.linalg.norm(t);p=ps[end];ss=dict(s)
   if end==0:ss['points']=[(p-.8*t).tolist(),(p+.2*t).tolist()]
   else:ss['points']=[(p-.2*t).tolist(),(p+.8*t).tolist()];ss['thinNormal']=(ps[-1]-np.array([26,0,115])).tolist()
   # Recover actual radial vector at the channel end, perpendicular to tangent
   # from the rectangle's transported frame, rather than guessed world axes.
   n=np.array(s['thinNormal']);ts=np.gradient(ps,axis=0);ts/=np.linalg.norm(ts,axis=1)[:,None]
   for tt in ts[:1] if end==0 else ts:n-=tt*(n@tt);n/=np.linalg.norm(n)
   ss['thinNormal']=n.tolist();tool=g.channel_solid(ss);hit=b^tool;assert hit.status()==mf.Error.NoError
   if hit.volume()>1e-8:b=b-tool;assert b.status()==mf.Error.NoError
 rows.append({'pose':i,'removedMm3':previous-b.volume()})
m=b.to_mesh64();np.savez(sp,vertices=m.vert_properties[:,:3],faces=m.tri_verts);r['stateSha256']=c.sha(sp);r['portsExtended']={'distanceMm':.8,'totalRemovedMm3':before-b.volume(),'details':rows,'workerSha256':c.sha(Path(__file__))};c.save(rp,r);print(json.dumps({'part':o.part,'removedMm3':before-b.volume(),'poses':len(rows)}))
