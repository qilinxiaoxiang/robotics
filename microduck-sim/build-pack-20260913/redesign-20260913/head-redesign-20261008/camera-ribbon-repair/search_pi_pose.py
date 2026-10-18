from pathlib import Path
import sys,json,itertools,hashlib
import numpy as np,trimesh,manifold3d as mf
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;H=D.parent;sys.path.insert(0,str(H/'cabling-release-20261008'));import check_routes as c
parts={'pi':c.obs['pi']}
for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']:
 parts[k]=c.man(c.load(H/'curved-head'/(k+'-world.stl')))
parts['zero_w_header_and_housing']=mf.Manifold.cube([18,52,7]).translate([49.31,-26.011755,116.0496])
center=np.array([68.11,-.0113773,131.0496]);mouth=np.array([65.8,32.4886208,131.0496]);parts['csi_straight_receiving']=mf.Manifold.cube([.6,7.6,16],True).translate(mouth+[0,3.8,0])
core=mf.Manifold.batch_boolean(list(parts.values()),mf.OpType.Add)
# Separate current printed mounts/other electronics to retain useful repack candidates.
skip={'pi','zero_w_populated_receiving','pi_usb_receiving','openrb_usb_receiving'}
fixed={k:v for k,v in c.obs.items() if k not in skip and v.bounding_box()[5]>100}
critical={k:v for k,v in fixed.items() if k not in ['face_panel','head_cap','openrb','amplifier','speaker','speaker_cradle','speaker_keeper','curved_cap_hardware']}
cu=mf.Manifold.batch_boolean(list(critical.values()),mf.OpType.Add)
rows=[];best=[];count=0
for roll,yaw in itertools.product([-15,-10,-5,0,5,10,15],[-25,-15,-5,0,5,15,25]):
 rot=Rotation.from_euler('xz',[roll,yaw],degrees=True).as_matrix()
 for dx,dy,dz in itertools.product([-3,0,3],[-3,0,3],[-3,0,3]):
  count+=1;T=np.eye(4);T[:3,:3]=rot;T[:3,3]=center+[dx,dy,dz]-rot@center;m=core.transform(T[:3]);cv=c.hits(m,cu)
  if cv>50:continue
  hits={k:c.hits(m,o) for k,o in fixed.items()};hits={k:v for k,v in hits.items() if v>1e-5};score=sum(hits.values());row={'rollXdeg':roll,'yawZdeg':yaw,'translationMm':[dx,dy,dz],'transform':T.tolist(),'criticalOverlapMm3':cv,'hitsMm3':hits,'sumOverlapMm3':score,'mouth':(T[:3,:3]@mouth+T[:3,3]).tolist()};rows.append(row);best.append(row);best.sort(key=lambda r:r['sumOverlapMm3']);best=best[:15]
 print(roll,yaw,'n',count,'retained',len(rows),'best',best[0]['sumOverlapMm3'] if best else None,flush=True)
r={'count':count,'rows':rows,'best':best,'acceptance':False,'fixedKeys':list(fixed),'sourceHashes':c.hashes,'straightEndEnvelope':'16mmwidth,0.6mmthickness,7.6mmoutsideCSI mouth;12mm totalreinforced section assuming4.4mminsertion, declareddesignreceivingbound notmanufacturerdata'};(D/'pi-pose-search.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(best[:3],indent=2))
