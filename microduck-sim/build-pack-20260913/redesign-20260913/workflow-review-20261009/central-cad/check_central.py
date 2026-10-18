from pathlib import Path
import json,base64,hashlib
import numpy as np
import trimesh
import manifold3d as mf
D=Path(__file__).resolve().parent
keys=['torso_base','power_support','shell_left','shell_right','regulator','regulator_insert','imu_clamp','fuse_carrier','motor11','motor12','motor5','motor10','yaw','right_yaw','ring10_torso','ring5_torso']
rows=[];sections={};hashes={}
def solid(mesh):
 s=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)));return s
banks={c:trimesh.creation.box(extents=e,transform=trimesh.transformations.translation_matrix([-5,0,-6]))for c,e in [('B',[65.9,26,80.9]),('C',[80.9,26,65.9])]};bs={k:solid(v)for k,v in banks.items()}
for key in keys:
 p=D/'current-mesh'/f'{key}.json';hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();a=json.loads(p.read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(a['positionB64']),dtype='<f4').reshape(-1,3),np.frombuffer(base64.b64decode(a['indexB64']),dtype='<u4').reshape(-1,3),process=True)
 dy=11 if key in ['motor10','yaw','ring10_torso']else -11 if key in ['motor5','right_yaw','ring5_torso']else 0;m.apply_translation([0,dy,0]);s=solid(m);valid=m.is_watertight and s.status()==mf.Error.NoError
 row={'key':key,'shiftY':dy,'meshWatertight':bool(m.is_watertight),'manifoldStatus':str(s.status()),'inputValid':bool(valid),'bounds':m.bounds.tolist(),'volumeMm3':float(s.volume())if valid else None,'batteryIntersectionsMm3':{},'aabbSeparationMm':{c:max(float(max(banks[c].bounds[0]-m.bounds[1])),float(max(m.bounds[0]-banks[c].bounds[1])))for c in banks},'batteryIntersectionBounds':{}}
 if valid:
  for c,b in bs.items():
   hit=s^b;assert hit.status()==mf.Error.NoError;row['batteryIntersectionsMm3'][c]=float(hit.volume());row['batteryIntersectionBounds'][c]=list(hit.bounding_box())if not hit.is_empty()else None
 sections[key]={}
 for axis,label in [(1,'Y0-side'),(2,'Z0-plan')]:
  n=np.eye(3)[axis];cut=m.section(plane_origin=[0,0,0],plane_normal=n);sections[key][label]=[path.tolist()for path in cut.discrete]if cut is not None else []
 rows.append(row);print(key,row['batteryIntersectionsMm3'],flush=True)
report={'scope':'Selected actual source mesh solids against B/C bank at neutral pose; no whole-scene motion claim.','bankClearanceInThisCheck':'Physical nominal box only; 1mm receiving tolerance not included in intersections.','rows':rows,'sections':sections,'sourceHashes':hashes,'recommendation':'C preferred for lower height. Both intersect fixed base/power occupancy; +22mm stance alone does not create a usable cavity. Must redesign central bridge and relocate converter/power support.','held':['No replacement structure designed yet.','No insertion or walking joint sweep accepted.','Open/invalid inputs retain explicit incomplete status, never zero-intersection pass.']}
(D/'selected-central-intersections.json').write_text(json.dumps(report,indent=2)+'\n')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="720"><rect width="1240" height="720" fill="#f6f8fa"/><defs><clipPath id="plot"><rect x="0" y="90" width="1240" height="500"/></clipPath></defs><g font-family="Arial"><text x="28" y="36" font-size="24">Actual central sections: C battery with both legs shifted 11 mm</text><text x="28" y="65" font-size="15">Blue: nominal battery. Red: existing fixed structure. Grey: shifted interfaces. NOT A NEW PRINT DESIGN.</text>']
for label,axes,origin,ctr in [('Y0-side',(0,2),[300,370],[-5,-6]),('Z0-plan',(0,1),[910,370],[-5,0])]:
 scale=4;proj=lambda p:(origin[0]+scale*p[axes[0]],origin[1]-scale*p[axes[1]])
 bb=banks['C'].bounds;x,y=proj(bb[0]);xx,yy=proj(bb[1]);svg.append(f'<rect x="{x}" y="{yy}" width="{xx-x}" height="{y-yy}" fill="#8ac6e1" opacity=".5" stroke="#29799c"/>')
 for row in rows:
  key=row['key'];col='#77838f'if row['shiftY']else '#b6534b'
  for path in sections[key][label]:
   pts=' '.join(f'{x:.2f},{y:.2f}'for x,y in map(proj,path));svg.append(f'<polyline clip-path="url(#plot)" points="{pts}" fill="none" stroke="{col}" stroke-width="1.3"><title>{key}</title></polyline>')
 svg.append(f'<text x="{origin[0]-260}" y="615" font-size="18">{label}: mesh-plane contours (not bounding rectangles)</text>')
svg.append('<text x="28" y="670" font-size="16">C: 80.9 X x 26 Y x 65.9 Z mm. B is 15 mm taller. Central base and converter region must be rebuilt.</text></g></svg>');(D/'actual-central-sections.svg').write_text('\n'.join(svg))
