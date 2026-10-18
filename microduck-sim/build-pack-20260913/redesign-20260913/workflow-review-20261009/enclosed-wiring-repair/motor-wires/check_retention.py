"""Finite existing-thigh wrap candidate, no printed additions."""
import json,math,hashlib
from pathlib import Path
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0;return a
def contour(x0,x1,y0,y1,r):
 pts=[]
 for x,y,st in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
  for ang in np.linspace(st,st+90,25,endpoint=False):pts.append([x+r*math.cos(math.radians(ang)),y+r*math.sin(math.radians(ang))])
 return pts
# +/-0.4 around centreline, body1.8 wide alongZ. Candidate lock5x5x3 on outerright.
outer=mf.CrossSection([contour(-45.9,17.4,-71.8,-66.8,1.6)])
inner=mf.CrossSection([contour(-45.1,16.6,-71.,-67.6,.8)])
strap=(outer-inner).extrude(1.8).translate([0,0,-28.7])
lock=mf.Manifold.cube([5,5,3]).translate([17.4,-72.5,-29.3]);parts={'strap':strap,'lock':lock};results=[]
for name,a in parts.items():
 m=a.to_mesh64();mesh=trimesh.Trimesh(m.vert_properties,m.tri_verts,process=True);assert mesh.is_watertight
 f=D/f'right-thigh-retention-{name}.stl';mesh.export(f);checks=[]
 for p in O.glob('*.json'):
  d=json.loads(p.read_text());bb=np.array(d['expectedFinalBoundsMm'])
  if np.any(mesh.bounds[1]<bb[0]) or np.any(bb[1]<mesh.bounds[0]):continue
  b=trimesh.load_mesh(d['file'],process=True);b.apply_translation(d.get('importTranslationMm',[0,0,0]));s=solid(b);cut=a^s
  checks.append({'key':d['key'],'sha256':d['sha256'],'overlapMm3':cut.volume(),'bounds':list(cut.bounding_box()) if cut.volume()>1e-7 else None})
 for i in range(1,4):
  p=D/f'retained-04-03-wire-{i}.stl';b=solid(trimesh.load_mesh(p,process=True));cut=a^b
  checks.append({'key':p.name,'sha256':sha(p),'overlapMm3':cut.volume(),'minGapMm':a.min_gap(b,2.) if cut.volume()<1e-7 else None})
 results.append({'part':name,'file':str(f),'sha256':sha(f),'bounds':mesh.bounds.tolist(),'checks':checks})
 print(name,[(x['key'],round(x['overlapMm3'],6),x.get('minGapMm')) for x in checks],flush=True)
(D/'retention-candidate.json').write_text(json.dumps({'status':'candidate; full loop body and lock represented, not stock confirmation','bodyReceivingMm':{'width':1.8,'thickness':.8},'lockReceivingMm':[5,5,3],'requiredMinimumLengthMm':150,'supplierPart':'unselected; existing71mm narrow tie insufficient','mountBody':'upper_leg_right','wrap':'Existing rear thigh shell, no new bracket; install before knee rear cover closes if threading access otherwise blocked. Threading motion not yet checked.','results':results},indent=2))
