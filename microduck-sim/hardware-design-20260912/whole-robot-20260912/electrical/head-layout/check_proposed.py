from geometry import *
import json
R=np.array([[0,0,1],[1,0,0],[0,1,0]])
recs=json.loads((HERE.parent/'sources/openrb-solid-bounds.json').read_text())
mm=manifold3d.Manifold.batch_boolean([cub(np.array(r['bounds_mm']).mean(0),np.ptp(np.array(r['bounds_mm']),axis=0)+1) for r in recs],manifold3d.OpType.Add).transform(np.c_[R,[24.5,0,-18]])
O=add_pi(obstacles(True));rs={}
parts=[('openrb',tri(mm),mm)]
for n,c,d in [('amp',[25,-27,-26],[12,22,21]),('imu',[25,-26,4],[8,25,28]),('speaker',[20,28,0],[6,21,31]),('openrb_usb_plug',[27.2,0,23.6],[7,12,15]),('pi_usb_data_plug',[35.435,8.9,-56.1],[10,10,6]),('pi_usb_power_plug',[35.435,21.5,-56.1],[10,10,6]),('pi_camera_connector',[15.435,35.49,-56.1],[12,6,6])]:parts.append((n,box(c,d),cub(c,d)))
for i,(n,m,mm) in enumerate(parts):
 rs[n]={'bounds_mm':m.bounds.tolist(),'collision_with_original_fixed_geometry':hits(mm,O),'collision_with_other_new_parts':hits(mm,parts[:i])}
print(json.dumps(rs,indent=2));(HERE/'proposed-before-cover.json').write_text(json.dumps(rs,indent=2)+'\n')
