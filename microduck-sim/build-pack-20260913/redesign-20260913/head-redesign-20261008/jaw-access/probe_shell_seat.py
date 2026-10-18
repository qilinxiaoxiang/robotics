from pathlib import Path
p=Path(__file__).resolve().parent.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns);globals().update(ns)
H=solid('head_bottom');S=solid('jaw_support');M=solid('motor15');neck={k:solid(k) for k in ['motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']}
relief=mf.Manifold()
for k in ['motor14','motor15','head_roll_ring_a','head_roll_ring_b']:relief+=solid(k).minkowski_sum(box([-.15,-.15,-.15],[.15,.15,.15]))
new=H-relief
print('SHELL',new.volume(),len(new.decompose()),'removed',(H-new).volume(),'bb',H.bounding_box(),new.bounding_box(),flush=True)
for name,m,f,v in [('shell',{'H':new},neck,[0,0,-40]),('S+M15',{'S':S,'M15':M},neck|{'H':new},[0,0,40])]:
 print(name,samples(m,f,v,step=.25)['peakContactsMm3'],flush=True)
m=new.to_mesh();trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False).export(Path(__file__).resolve().parent/'head_bottom-internal-seat-clearance-world.stl')
