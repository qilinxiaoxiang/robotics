from pathlib import Path
import sys,json,itertools,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;sys.path.insert(0,str(H/'cabling-release-20261008'));import check_routes as c
parts={'pi':c.obs['pi']}
for k in ['zero_w_components','zero_w_gpio_solder_tails']:parts[k]=c.man(c.load(H/'curved-head'/(k+'-world.stl')))
parts['zero_w_header_and_housing']=mf.Manifold.cube([18,52,7]).translate([49.31,-26.011755,116.0496]);mouth=np.array([65.8,32.4886208,131.0496]);parts['csi_straight']=mf.Manifold.cube([.6,7.6,16],True).translate(mouth+[0,3.8,0]);center=np.array([68.11,-.0113773,131.0496]);core=mf.Manifold.batch_boolean(list(parts.values()),mf.OpType.Add)
# For a meaningful layout search only existing board/audio mounts may be redesigned;
# source curved skin is preserved as a real mesh, plus all mechanical/head obstacles.
skip={'pi','zero_w_populated_receiving','pi_usb_receiving','openrb_usb_receiving','openrb','speaker','amplifier','speaker_cradle','speaker_keeper','curved_cap_hardware','head_cap'}
fixed={k:v for k,v in c.obs.items() if k not in skip and v.bounding_box()[5]>100};fixed['native_curved_skin']=c.man(c.load(H/'curved-head/community-curved-head-world.stl'))
union=mf.Manifold.batch_boolean(list(fixed.values()),mf.OpType.Add);B=np.array([[0,0,1],[1,0,0],[0,1,0]],float)
rows=[];best=[];count=0
for longsign,widthsign in itertools.product([-1,1],repeat=2):
 L=np.array([longsign,0,0]);W=np.array([0,widthsign,0]);Rot=np.stack([L,W,np.cross(L,W)],axis=1)@B.T
 for x,y,z in itertools.product([25,30,35,40,45],[-24,-21,-18,-15,15,18,21,24],[134,136,138,140,142,144,146]):
  count+=1;T=np.eye(4);T[:3,:3]=Rot;T[:3,3]=[x,y,z]-Rot@center;obj=core.transform(T[:3]);score=c.hits(obj,union)
  row={'centerMm':[x,y,z],'longsign':longsign,'widthsign':widthsign,'transform':T.tolist(),'unionOverlapMm3':score}
  if score<1e-5:rows.append(row)
  best.append(row);best.sort(key=lambda r:r['unionOverlapMm3']);best=best[:12]
 print('orientation',longsign,widthsign,'clear',len(rows),'best',best[0]['unionOverlapMm3'],flush=True)
for row in best:
 m=core.transform(np.array(row['transform'])[:3]);row['hitsMm3']={k:c.hits(m,o) for k,o in fixed.items() if c.hits(m,o)>1e-5}
(D/'horizontal-side-pi-search.json').write_text(json.dumps({'count':count,'clear':rows,'best':best,'fixedKeys':list(fixed),'excludedOnlyForProposedRepack':list(skip),'accepted':False,'sourceHashes':c.hashes},indent=2)+'\n');print(json.dumps(best[:3],indent=2))
