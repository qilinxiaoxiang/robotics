from pathlib import Path
import json,hashlib,trimesh,numpy as np,manifold3d as mf
D=Path(__file__).resolve().parent;SIM=D.parents[5]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
 m=trimesh.load_mesh(p);assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
src=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/compact-battery/power-support-integrated-body.stl';dst=D/'power-support-controller-concept-world.stl';old=load(src);new=load(dst);rows=[]
for y in [-9.5,9.5]:
 protect=mf.Manifold.cylinder(40,2.5,2.5,64).translate([-16.5,y,-8]);a=(old-new)^protect;b=(new-old)^protect;rows.append({'axisXY':[-16.5,y],'zSpan':[-8,32],'radiusMm':2.5,'removedVolumeMm3':a.volume(),'addedVolumeMm3':b.volume()})
p=D/'mount-interface-check.json';p.write_text(json.dumps({'sourceHashes':{str(src):sha(src),str(dst):sha(dst)},'scope':'Both +/-Y columns include original upper and lower M2x10 support interfaces. Same material inside R2.5 and Z-8..32 preserves original seats/hole walls/stack. Side braces outside this region transfer carrier load; no strength experiment claimed.','rows':rows,'passed':all(abs(r['removedVolumeMm3'])<1e-6 and abs(r['addedVolumeMm3'])<1e-6 for r in rows)},indent=2));print(rows)
