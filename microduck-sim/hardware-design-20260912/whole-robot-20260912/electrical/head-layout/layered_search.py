from geometry import *
import json,itertools,time
records=json.loads((HERE.parent/'sources/openrb-solid-bounds.json').read_text())
components=[]
for r in records:
 b=np.array(r['bounds_mm']);components.append(cub(b.mean(0),(b[1]-b[0])+0.10))
shape=manifold3d.Manifold.batch_boolean(components,manifold3d.OpType.Add)
# Native STEP X=25mm width, Y=66mm length, Z=board normal; map to body Y,Z,X.
R=np.array([[0,0,1],[1,0,0],[0,1,0]])
obs=add_pi(obstacles());fixed=add_pi(obstacles(True));results=[]
for x,y,z in itertools.product([24,27,30,33,34,35],[0,-5,5],[-20,-17,-14]):
 c=np.array([x,y,z]);mm=shape.transform(np.c_[R,c]);actual=hits(mm,fixed)
 results.append({'board_origin_body_mm':c.tolist(),'rotation':R.tolist(),'with_fixed_structure_collisions':actual,'with_original_shell_collisions':hits(mm,obs),'bounds_mm':tri(mm).bounds.tolist()})
(HERE/'openrb-layered-candidates.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps([r for r in results if not r['with_fixed_structure_collisions']][:12],indent=2))
tri(shape).export(HERE/'openrb-layered-envelope.stl')
