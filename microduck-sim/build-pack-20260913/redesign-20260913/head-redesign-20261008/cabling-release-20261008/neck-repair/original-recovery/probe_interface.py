from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
out={}
for z in [-7,-5,-3,-1,0]:
 it=J.translate([0,0,z])^V;m=it.to_mesh64();v=np.asarray(m.vert_properties)[:,:3];out[str(z)]={'volume':it.volume(),'bounds':None if not len(v) else [v.min(0).tolist(),v.max(0).tolist()]}
for y in [-.2,-.3,-.5]:
 it=M.translate([0,y,0])^V;out['motor_offset'+str(y)]={'shell':it.volume(),'jaw':(M.translate([0,y,0])^J).volume()}
for a in [-30,-60]:
 p=np.array([26.1,0,118.6146]);j=J.translate(-p).rotate([0,a,0]).translate(p)
 out['jaw_angle'+str(a)]={'final':(j^V).volume(),'topPeak':max((j.translate([0,0,float(z)])^V).volume() for z in np.linspace(40,0,81))}
c.save(D/'interface-diagnostic.json',out);print(json.dumps(out))
