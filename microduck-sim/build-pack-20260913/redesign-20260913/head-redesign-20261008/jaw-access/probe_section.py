from pathlib import Path
p=Path(__file__).resolve().parent.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns);globals().update(ns)
jaw=solid('jaw_frame');print('bounds',jaw.bounding_box());m=jaw.to_mesh();tm=trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts));section=tm.section([0,1,0],[0,-30,0]);print('SECTIONS')
for c in section.discrete:print(np.min(c,axis=0),np.max(c,axis=0));print(c.tolist())
# Whole-head pad route with the original source pad/geometry.
pivot=np.array([26.1,0,118.6146]);fixed={k:solid(k) for k in ['jaw_support','head_bottom','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b','jaw_frame']}
for a in [0,30]:
 jf=jaw.translate(-pivot).rotate([0,a,0]).translate(pivot);pad=solid('lower_pad').translate(-pivot).rotate([0,a,0]).translate(pivot);fixed['jaw_frame']=jf
 for v in [[32,0,0],[0,0,32],[0,0,-32],[16,0,27.7128],[40,0,-3]]:
  r=samples({'pad':pad},fixed,v,step=.5);print('PAD',a,v,r['peakContactsMm3'],flush=True)
