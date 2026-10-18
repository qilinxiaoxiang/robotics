from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
R=ring(10.4,14.4,2.4,-39.55);out={'scope':'Rigid local-ear offset only; not a deformation model or PLA elastic acceptance','earProxyClipYAbsMm':30,'rows':[]}
ears={-1:J^mf.Manifold.cube([200,70,200]).translate([-50,-100,0]),1:J^mf.Manifold.cube([200,70,200]).translate([-50,30,0])}
for z in [-15,-12,-10,-8,-6,-4,-2,-1,0]:
 row={'offsetZ':z,'requiredOutwardOffsetByEarMm':{}}
 for sign,e in ears.items():
  def hit(d):return (e.translate([0,sign*d,z])^V).volume()>1e-7
  if not hit(0):d=0
  else:
   lo,hi=0.,8.;assert not hit(hi)
   for i in range(14):
    m=(lo+hi)/2
    if hit(m):lo=m
    else:hi=m
   d=hi
  row['requiredOutwardOffsetByEarMm'][str(sign)]=d
 out['rows'].append(row)
for k,s in [('jaw',J),('support',S)]:
 v=np.asarray(s.to_mesh64().vert_properties)[:,:3];a=v[(v[:,1]<-36.9)&(v[:,1]>-40.1)];r=np.sqrt((a[:,0]-26.1)**2+(a[:,2]-118.6146)**2);sel=r[r<2.5];out[k+'CentralHoleRadiiNearPassiveBoss']=sorted(set(np.round(sel,4).tolist()))[:40]
out['sourceHashes']={str(p.resolve()):c.sha(p) for p in inputs};c.save(D/'ear-splay-diagnostic.json',out);print(json.dumps(out))
