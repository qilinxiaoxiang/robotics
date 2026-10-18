from pathlib import Path
import json,hashlib,base64
import numpy as np
import trimesh
import manifold3d as mf
D=Path(__file__).resolve().parent;spec=json.loads((D/'central-bridge-primitives.json').read_text());contract=json.loads((D/'current-coordinate-contract.json').read_text());parts={p['key']:p for p in contract['parts']}
def body(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
sol=[]
for p in spec['primitiveSolids']:
 m=trimesh.creation.box(extents=p['dimensionsMm']);m.apply_translation(np.array(p['originMinMm'])+np.array(p['dimensionsMm'])/2);sol.append(body(m))
frame=mf.Manifold.batch_boolean(sol,mf.OpType.Add);assert frame.status()==mf.Error.NoError
b=spec['batterySolid'];bank=mf.Manifold.cube(b['dimensionsMm']).translate(b['originMinMm']);rows=[{'key':'battery-lowered8','representation':'nominal box','intersectionMm3':float((frame^bank).volume()),'minimumGapMm':float(frame.min_gap(bank,2))}]
keys=contract['leftShiftedKeys']+contract['rightShiftedKeys']+[p['key']for p in contract['parts']if p.get('moduleId')=='neck'and p['key']not in ['shell_left','shell_right']]
keys=sorted(set(keys)|{'motor11','motor12'});hashes={}
for key in keys:
 p=D/'current-mesh'/f'{key}.json';a=json.loads(p.read_text());hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();m=trimesh.Trimesh(np.frombuffer(base64.b64decode(a['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(a['indexB64']),'<u4').reshape(-1,3),process=True);m.apply_translation(parts[key]['cLayoutTranslationMm']);s=body(m);mode='source mesh'
 if not m.is_watertight or s.status()!=mf.Error.NoError:
  m=m.convex_hull;s=body(m);mode='closed convex hull enclosing all source vertices (conservative; overlaps may be false positives)'
 assert s.status()==mf.Error.NoError
 hit=frame^s;assert hit.status()==mf.Error.NoError
 row={'key':key,'representation':mode,'intersectionMm3':float(hit.volume()),'minimumGapMm':float(frame.min_gap(s,5)),'gapCappedAtMm':5};rows.append(row);print(key,row['intersectionMm3'],row['minimumGapMm'],flush=True)
mesh=frame.to_mesh();trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(D/'central-bridge-skeleton-world.stl')
r={'status':'STATIC SKELETON DIAGNOSTIC, NOT PRINT RELEASE','frameManifoldStatus':str(frame.status()),'frameComponents':len(frame.decompose()),'partCount':len(keys),'rows':rows,'allCheckedClear':all(x['intersectionMm3']<1e-7 for x in rows),'excludedReplacedBaseline':['torso_base','shell_left','shell_right','power_support','regulator','regulator_insert','fuse_carrier'],'scope':'Only proposed structural primitives against intact shifted leg groups and fixed/current neck components at neutral pose. Legacy replaced central solids intentionally shown separately. No joint motion/strength/installed hardware pass.','sourceHashes':{**hashes,**{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [D/'central-bridge-primitives.json',Path(__file__)]}}};(D/'central-bridge-static.json').write_text(json.dumps(r,indent=2)+'\n')
